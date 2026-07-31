from dataclasses import dataclass
from pathlib import Path

import pdfplumber


class TextExtractionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class ExtractedText:
    full_text: str
    page_count: int
    pages: list[str]
    char_count: int


def extract_text_from_pdf(file_path: Path) -> ExtractedText:
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as e:
        raise TextExtractionError(f"Could not extract text from PDF: {e}") from e

    full_text = "\n\n".join(pages)
    return ExtractedText(
        full_text=full_text,
        page_count=len(pages),
        pages=pages,
        char_count=len(full_text),
    )
