import magic

from app.core.config import settings


class UploadValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def validate_file_size(size_bytes: int) -> None:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise UploadValidationError(
            f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
            413
        )
    
    if size_bytes == 0:
        raise UploadValidationError(
            "Uploaded file is empty",
            400
        )
    
def  validate_content_type(content: bytes) -> str:
    """Detect the real content type from file bytes (magic numbers), not the client-supplied header.

    Returns the detected content type if valid, raises otherwise.
    """
    detected_type = magic.from_buffer(content, mime=True)
    if detected_type not in settings.allowed_content_types:
        raise UploadValidationError(
            f"File type '{detected_type}' is not supported. "
            f"Allowed types: {', '.join(settings.allowed_content_types)}",
            415
        )
    return detected_type