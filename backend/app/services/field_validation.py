from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.core.config import settings
from app.services.llm_extraction import InvoiceExtractionSchema

REQUIRED_FIELDS = {"invoice_number", "invoice_date", "total_amount"}
NON_NEGATIVE_AMOUNT_FIELDS = {"subtotal", "tax_amount", "total_amount"}
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y")
_CURRENCY_RE_LEN = 3


@dataclass
class FieldResult:
    field_name: str
    value: Any
    confidence_score: float
    is_flagged: bool
    flag_reasons: list[str] = field(default_factory=list)


def _normalize_date(raw: str | None) -> tuple[str | None, bool]:
    """Returns (normalized ISO string or original raw value, parsed_ok)."""
    if raw is None:
        return None, True
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat(), True
        except ValueError:
            continue
    return raw, False


def _amounts_reconcile(a: float, b: float) -> bool:
    tolerance = max(settings.cross_field_tolerance * max(abs(a), abs(b), 1.0), 0.01)
    return abs(a - b) <= tolerance


def normalize_and_score_fields(extracted: InvoiceExtractionSchema) -> list[FieldResult]:
    deductions: dict[str, list[tuple[float, str]]] = {
        name: [] for name in InvoiceExtractionSchema.model_fields
    }
    values: dict[str, Any] = {}

    invoice_date_iso, invoice_date_ok = _normalize_date(extracted.invoice_date)
    due_date_iso, due_date_ok = _normalize_date(extracted.due_date)
    values["invoice_date"] = invoice_date_iso
    values["due_date"] = due_date_iso

    if extracted.invoice_date is not None and not invoice_date_ok:
        deductions["invoice_date"].append((0.5, "date format not recognized"))
    if extracted.due_date is not None and not due_date_ok:
        deductions["due_date"].append((0.5, "date format not recognized"))

    if invoice_date_ok and due_date_ok and invoice_date_iso and due_date_iso:
        if date.fromisoformat(due_date_iso) < date.fromisoformat(invoice_date_iso):
            deductions["invoice_date"].append((0.3, "due date is before invoice date"))
            deductions["due_date"].append((0.3, "due date is before invoice date"))

    for name in NON_NEGATIVE_AMOUNT_FIELDS:
        amount = getattr(extracted, name)
        if amount is not None and amount < 0:
            deductions[name].append((0.5, "amount is negative"))

    line_items_total = sum(
        item.line_total for item in extracted.line_items if item.line_total is not None
    )
    has_line_item_totals = any(item.line_total is not None for item in extracted.line_items)
    if extracted.subtotal is not None and has_line_item_totals:
        if not _amounts_reconcile(line_items_total, extracted.subtotal):
            deductions["subtotal"].append((0.4, "line items do not sum to subtotal"))
            deductions["line_items"].append((0.4, "line items do not sum to subtotal"))

    if (
        extracted.subtotal is not None
        and extracted.tax_amount is not None
        and extracted.total_amount is not None
    ):
        if not _amounts_reconcile(extracted.subtotal + extracted.tax_amount, extracted.total_amount):
            reason = "subtotal + tax does not equal total"
            deductions["subtotal"].append((0.4, reason))
            deductions["tax_amount"].append((0.4, reason))
            deductions["total_amount"].append((0.4, reason))

    for item in extracted.line_items:
        if item.quantity is not None and item.unit_price is not None and item.line_total is not None:
            if not _amounts_reconcile(item.quantity * item.unit_price, item.line_total):
                deductions["line_items"].append(
                    (0.2, f"line item '{item.description}' quantity*unit_price != line_total")
                )

    if extracted.currency is not None:
        currency = extracted.currency.strip()
        if len(currency) != _CURRENCY_RE_LEN or not currency.isalpha() or not currency.isupper():
            deductions["currency"].append((0.2, "currency is not a 3-letter uppercase code"))

    results: list[FieldResult] = []
    for name in InvoiceExtractionSchema.model_fields:
        if name == "line_items":
            raw_value = [item.model_dump() for item in extracted.line_items]
            is_present = len(raw_value) > 0
        else:
            raw_value = values.get(name, getattr(extracted, name))
            is_present = raw_value is not None

        if is_present:
            presence_component = 1.0
        elif name in REQUIRED_FIELDS:
            presence_component = 0.0
        else:
            presence_component = 0.85

        field_deductions = deductions[name]
        validation_component = max(0.0, 1.0 - sum(d for d, _ in field_deductions))

        confidence = round(presence_component * validation_component, 3)
        confidence = max(0.0, min(1.0, confidence))

        results.append(
            FieldResult(
                field_name=name,
                value=raw_value,
                confidence_score=confidence,
                is_flagged=confidence < settings.field_flag_threshold,
                flag_reasons=[reason for _, reason in field_deductions],
            )
        )

    return results
