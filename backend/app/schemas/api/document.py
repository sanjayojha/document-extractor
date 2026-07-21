
from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    document_type: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

class DocumentUploadResponse(DocumentResponse):
    is_duplicate: bool = False
