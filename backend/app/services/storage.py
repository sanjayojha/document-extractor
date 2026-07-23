from pathlib import Path
import uuid

from app.core.config import settings


def build_storage_path(document_id: uuid.UUID, original_filename: str) -> Path:
    """Build the on-disk path for a stored document, keyed by UUID not user filename."""
    extension = Path(original_filename).suffix # includes the leading dot, e.g. ".pdf"
    return Path(settings.storage_dir) / f"{document_id}{extension}"

def save_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)