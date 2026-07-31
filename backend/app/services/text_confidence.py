import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.pdf_text import ExtractedText

_KEYWORDS = (
    "invoice", "total", "subtotal", "amount due", "date",
    "bill to", "qty", "description", "tax",
)
_LEGIBLE_CHARS_RE = re.compile(r"[a-zA-Z0-9\s.,\-/:;()$%]")


@dataclass
class TextConfidenceResult:
    score: float
    has_usable_text: bool
    reasons: list[str] = field(default_factory=list)


def score_text_extraction(extracted: ExtractedText) -> TextConfidenceResult:
    if extracted.char_count == 0 or extracted.page_count == 0:
        return TextConfidenceResult(
            score=0.0, has_usable_text=False, reasons=["no extractable text layer"]
        )

    chars_per_page = extracted.char_count / extracted.page_count
    density = min(chars_per_page / 200, 1.0)

    legible_chars = sum(1 for c in extracted.full_text if _LEGIBLE_CHARS_RE.match(c))
    legibility = legible_chars / extracted.char_count

    lowered = extracted.full_text.lower()
    hits = sum(1 for kw in _KEYWORDS if kw in lowered)
    keyword_score = min(hits / 3, 1.0)

    score = round(0.5 * density + 0.3 * legibility + 0.2 * keyword_score, 3)
    score = max(0.0, min(1.0, score))

    reasons: list[str] = []
    if density < 0.5:
        reasons.append("low text density per page")
    if legibility < 0.7:
        reasons.append("extracted text mostly illegible/garbled")
    if hits == 0:
        reasons.append("no invoice-shaped keywords found")

    has_usable_text = score >= settings.min_text_confidence
    return TextConfidenceResult(score=score, has_usable_text=has_usable_text, reasons=reasons)


def score_non_pdf_document(content_type: str) -> TextConfidenceResult:
    return TextConfidenceResult(
        score=0.0,
        has_usable_text=False,
        reasons=[f"'{content_type}' has no text layer; OCR is not supported yet"],
    )
