from app.services.pdf_text import ExtractedText
from app.services.text_confidence import score_non_pdf_document, score_text_extraction


def _extracted(text: str, page_count: int = 1) -> ExtractedText:
    return ExtractedText(
        full_text=text, page_count=page_count, pages=[text], char_count=len(text)
    )


def test_dense_invoice_shaped_text_scores_high():
    text = (
        "INVOICE\nInvoice Number: INV-1001\nInvoice Date: 2026-01-15\n"
        "Bill To: Acme Corp\nDescription Qty Unit Price\n"
        "Widget A 2 10.00 20.00\nSubtotal: 20.00\nTax: 2.00\nTotal: 22.00\n"
        + ("padding text to raise character density. " * 6)
    )
    result = score_text_extraction(_extracted(text))

    assert result.has_usable_text is True
    assert result.score >= 0.35


def test_empty_text_scores_zero():
    result = score_text_extraction(_extracted("", page_count=1))

    assert result.score == 0.0
    assert result.has_usable_text is False
    assert "no extractable text layer" in result.reasons


def test_zero_pages_scores_zero():
    result = score_text_extraction(_extracted("", page_count=0))

    assert result.score == 0.0
    assert result.has_usable_text is False


def test_sparse_gibberish_text_scores_low():
    result = score_text_extraction(_extracted("\x01\x02\x03 x", page_count=1))

    assert result.has_usable_text is False


def test_non_pdf_png_scores_zero():
    result = score_non_pdf_document("image/png")

    assert result.score == 0.0
    assert result.has_usable_text is False


def test_non_pdf_jpeg_scores_zero():
    result = score_non_pdf_document("image/jpeg")

    assert result.score == 0.0
    assert result.has_usable_text is False
