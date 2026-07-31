import pytest

from app.services.pdf_text import TextExtractionError, extract_text_from_pdf


def test_extracts_real_text_from_invoice_pdf(tmp_path, sample_invoice_pdf_bytes):
    path = tmp_path / "invoice.pdf"
    path.write_bytes(sample_invoice_pdf_bytes)

    result = extract_text_from_pdf(path)

    assert result.page_count == 1
    assert result.char_count > 0
    assert "Invoice Number: INV-1001" in result.full_text
    assert "Total: 22.00" in result.full_text
    assert len(result.pages) == 1


def test_empty_page_pdf_returns_zero_pages(tmp_path, sample_pdf_bytes):
    path = tmp_path / "empty.pdf"
    path.write_bytes(sample_pdf_bytes)

    result = extract_text_from_pdf(path)

    assert result.page_count == 0
    assert result.char_count == 0
    assert result.full_text == ""


def test_missing_file_raises_text_extraction_error(tmp_path):
    missing_path = tmp_path / "does-not-exist.pdf"

    with pytest.raises(TextExtractionError):
        extract_text_from_pdf(missing_path)


def test_corrupt_pdf_raises_text_extraction_error(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"not a real pdf at all")

    with pytest.raises(TextExtractionError):
        extract_text_from_pdf(path)
