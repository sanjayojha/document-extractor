from app.models.document import Document

def test_upload_pdf_creates_document(client, storage_dir, sample_pdf_bytes):
    response = client.post(
        "/documents",
        files = {"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "invoice.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["status"] == "pending"
    assert data["is_duplicate"] is False

def test_upload_same_file_twice_returns_duplicate(client, storage_dir, sample_pdf_bytes):
    first = client.post("/documents", files = {"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")})
    second = client.post("/documents", files = {"file": ("invoice_copy.pdf", sample_pdf_bytes, "application/pdf")})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["is_duplicate"] is True
    assert second.json()["id"] == first.json()["id"]

def test_upload_rejects_unsupported_file_type(client, storage_dir, sample_text_bytes):
    response = client.post(
        "/documents", files={"file": ("notes.txt", sample_text_bytes, "text/plain")}
    )

    assert response.status_code == 415

def test_upload_rejects_oversized_file(client, storage_dir, monkeypatch, sample_pdf_bytes):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)  # even tiny files now exceed the limit
    response = client.post(
        "/documents", files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 413

def test_file_actually_saved_to_disk(client, storage_dir, sample_pdf_bytes):
    response = client.post(
        "/documents", files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")}
    )
    document_id = response.json()["id"]

    saved_files = list(storage_dir.glob(f"{document_id}.*"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == sample_pdf_bytes

def test_list_documents_returns_uploaded_documents(client, storage_dir, sample_pdf_bytes):
    client.post(
        "/documents", files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")}
    )

    response = client.get("/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_list_documents_filters_by_status(client, storage_dir, sample_pdf_bytes):
    client.post(
        "/documents", files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")}
    )

    response = client.get("/documents", params={"status_filter": "processing"})
    assert response.status_code == 200
    assert response.json() == []

def test_get_document_by_id(client, storage_dir, sample_pdf_bytes):
    upload_response = client.post("/documents", files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")})

    document_id = upload_response.json()["id"]

    response = client.get("/documents/"f"{document_id}")

    assert response.status_code == 200
    assert response.json()["id"] == document_id

def test_get_document_not_found_returns_404(client, storage_dir):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/documents/{fake_id}")

    assert response.status_code == 404
