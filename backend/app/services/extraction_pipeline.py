from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ExtractionStatus
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.extraction_field import ExtractionField
from app.services.field_validation import normalize_and_score_fields
from app.services.llm_extraction import (
    SCHEMA_VERSION,
    LLMExtractionError,
    call_openai_extraction,
)
from app.services.pdf_text import TextExtractionError, extract_text_from_pdf
from app.services.text_confidence import (
    TextConfidenceResult,
    score_non_pdf_document,
    score_text_extraction,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_extraction_pipeline(db: Session, document: Document, attempt_number: int) -> Extraction:
    extraction = Extraction(
        document_id=document.id,
        attempt_number=attempt_number,
        model_name=settings.openai_model,
        schema_version=SCHEMA_VERSION,
        status=ExtractionStatus.PROCESSING,
        started_at=_now(),
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    text_conf: TextConfidenceResult
    raw_text = ""
    if document.content_type != "application/pdf":
        text_conf = score_non_pdf_document(document.content_type)
    else:
        try:
            extracted = extract_text_from_pdf(Path(document.storage_path))
            text_conf = score_text_extraction(extracted)
            raw_text = extracted.full_text
        except TextExtractionError as e:
            text_conf = score_non_pdf_document(document.content_type)
            text_conf.reasons = [e.message]

    if not text_conf.has_usable_text:
        extraction.status = ExtractionStatus.LOW_CONFIDENCE
        extraction.error_message = "; ".join(text_conf.reasons) or "text confidence too low"
        extraction.completed_at = _now()
        db.commit()
        db.refresh(extraction)
        return extraction

    try:
        llm_result = call_openai_extraction(raw_text)
    except LLMExtractionError as e:
        extraction.status = ExtractionStatus.FAILED
        extraction.error_message = e.message
        extraction.completed_at = _now()
        db.commit()
        db.refresh(extraction)
        return extraction

    extraction.raw_llm_response = llm_result.raw_response
    extraction.model_name = llm_result.model

    field_results = normalize_and_score_fields(llm_result.parsed)
    for result in field_results:
        db.add(
            ExtractionField(
                extraction_id=extraction.id,
                field_name=result.field_name,
                field_value=result.value,
                confidence_score=result.confidence_score,
                is_flagged=result.is_flagged,
            )
        )

    extraction.status = ExtractionStatus.COMPLETED
    extraction.completed_at = _now()
    db.commit()
    db.refresh(extraction)
    return extraction
