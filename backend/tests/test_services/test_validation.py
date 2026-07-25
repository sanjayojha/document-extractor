
import pytest
from app.services.validation import UploadValidationError, validate_file_size, validate_content_type

def test_validate_file_size_accepts_normal_size():
    validate_file_size(1024)

def test_validate_file_size_rejects_oversized(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    with pytest.raises(UploadValidationError) as exc_info:
        validate_file_size(2 * 1024 * 1024)
    assert exc_info.value.status_code == 413

def test_validate_file_size_rejects_empty():
    with pytest.raises(UploadValidationError) as exc_info:
        validate_file_size(0)
    assert exc_info.value.status_code == 400

def test_validate_content_type_accepts_pdf(sample_pdf_bytes):
    result = validate_content_type(sample_pdf_bytes)
    assert result == "application/pdf"

def test_validate_content_type_accepts_png(sample_png_bytes):
    result = validate_content_type(sample_png_bytes)
    assert result == "image/png"

def test_validate_content_type_rejects_plain_text(sample_text_bytes):
    with pytest.raises(UploadValidationError) as exc_info:
        validate_content_type(sample_text_bytes)
    assert exc_info.value.status_code == 415