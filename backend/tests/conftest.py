
import os
# Must happen before any `app.*` import — overrides DATABASE_URL for the whole test session
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://docextractor_user:docextractor_pass@localhost:5432/docextractor_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.main import app
from app.api.deps import get_db

# Import models so Base.metadata knows about them
from app.models import Document, Extraction, ExtractionField  # noqa: F401

test_engine = create_engine(settings.database_url)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session, drop them when the session ends."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture()
def db_session():
    """Each test gets its own transaction, rolled back at the end — full isolation, no cross-test leakage."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with the real DB dependency swapped for our per-test session."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture()
def storage_dir(tmp_path, monkeypatch):
    """Redirect file storage to a pytest tmp_path so tests never touch the real storage/ folder."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    return tmp_path


@pytest.fixture()
def sample_pdf_bytes() -> bytes:
    """Minimal but valid-enough PDF for magic-byte detection to recognize as application/pdf."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n"
        b"%%EOF"
    )


@pytest.fixture()
def sample_png_bytes() -> bytes:
    """Minimal valid PNG signature + IHDR chunk — enough for magic-byte detection as image/png."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\x0dIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )


@pytest.fixture()
def sample_text_bytes() -> bytes:
    """Plain text — used to confirm invalid types get rejected."""
    return b"just some plain text, not a real document"


def _build_pdf(lines: list[str]) -> bytes:
    """Hand-rolled single-page PDF with a real Tj-based content stream and a
    correct xref table, so pdfplumber/pdfminer can actually extract the text
    (unlike sample_pdf_bytes above, which has an empty page tree)."""
    content_lines = ["BT", "/F1 12 Tf", "50 750 Td"]
    for i, line in enumerate(lines):
        if i > 0:
            content_lines.append("0 -20 Td")
        content_lines.append(f"({line}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n"
        + content_stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode()
        pdf += obj
        pdf += b"\nendobj\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()

    return bytes(pdf)


@pytest.fixture()
def sample_invoice_pdf_bytes() -> bytes:
    """A one-page PDF with real, extractable, invoice-shaped text."""
    return _build_pdf(
        [
            "INVOICE",
            "Invoice Number: INV-1001",
            "Invoice Date: 2026-01-15",
            "Due Date: 2026-02-15",
            "Bill To: Acme Corp",
            "Vendor: Example Vendor Inc",
            "Description Qty UnitPrice Amount",
            "Widget A 2 10.00 20.00",
            "Subtotal: 20.00",
            "Tax: 2.00",
            "Total: 22.00",
        ]
    )