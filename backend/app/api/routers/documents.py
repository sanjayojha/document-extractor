import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.api.document import DocumentResponse, DocumentUploadResponse
from app.db.session import get_db
from app.models.document import Document
from app.services.hashing import compute_sha256
from app.services.storage import build_storage_path, save_file
from app.services.validation import UploadValidationError, validate_content_type, validate_file_size


router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db)
) -> DocumentUploadResponse:
    content = await file.read()

    try:
        validate_file_size(len(content))
        detected_content_type = validate_content_type(content)
    except UploadValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    file_hash = compute_sha256(content)

    existing_stmt = select(Document).where(Document.file_hash == file_hash)
    existing = db.execute(existing_stmt).scalar_one_or_none()
    if existing is not None:
        response = DocumentUploadResponse.model_validate(existing, from_attributes=True)
        response.is_duplicate = True
        return response

    document = Document(
        id= uuid.uuid4(),
        original_filename= file.filename or "unknown",
        content_type=detected_content_type,
        file_size_bytes=len(content),
        file_hash=file_hash,
        status="pending",
    )

    storage_path = build_storage_path(document.id, document.original_filename)
    document.storage_path = str(storage_path)

    save_file(storage_path, content)

    db.add(document)
    db.commit()
    db.refresh(document)

    return DocumentUploadResponse.model_validate(document, from_attributes=True)



@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Document.status == status_filter)
    stmt = stmt.offset(offset).limit(limit)

    return list(db.execute(stmt).scalars().all())



@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Document:
    stmt = select(Document).where(Document.id == document_id)
    document = db.execute(stmt).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found!")
    return document
