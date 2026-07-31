from dataclasses import dataclass

import openai
from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings

SCHEMA_VERSION = "invoice_v1"

SYSTEM_PROMPT = (
    "You are an invoice data extraction assistant. You will be given raw text "
    "extracted from a PDF invoice via a text-layer extractor (spacing may be "
    "irregular due to table layouts). Extract the fields in the schema. If a "
    "field cannot be determined, return null — do not guess. Normalize dates "
    "to YYYY-MM-DD. Return amounts as plain numbers with no currency symbols."
)


class InvoiceLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    line_total: float | None = None


class InvoiceExtractionSchema(BaseModel):
    vendor_name: str | None = None
    vendor_address: str | None = None
    vendor_tax_id: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    po_number: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    bill_to_name: str | None = None
    bill_to_address: str | None = None
    line_items: list[InvoiceLineItem] = []


@dataclass
class LLMExtractionResult:
    parsed: InvoiceExtractionSchema
    model: str
    raw_response: dict


class LLMExtractionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def call_openai_extraction(raw_text: str, *, model: str | None = None) -> LLMExtractionResult:
    truncated_text = raw_text[: settings.max_llm_input_chars]

    try:
        completion = _get_client().chat.completions.parse(
            model=model or settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": truncated_text},
            ],
            response_format=InvoiceExtractionSchema,
            timeout=settings.llm_request_timeout_seconds,
        )
    except openai.OpenAIError as e:
        raise LLMExtractionError(f"OpenAI extraction call failed: {e}") from e

    choice = completion.choices[0]
    if choice.message.refusal:
        raise LLMExtractionError(f"Model refused to extract: {choice.message.refusal}")
    if choice.message.parsed is None:
        raise LLMExtractionError("Model returned no parsed extraction result")

    return LLMExtractionResult(
        parsed=choice.message.parsed,
        model=completion.model,
        raw_response=completion.model_dump(mode="json"),
    )
