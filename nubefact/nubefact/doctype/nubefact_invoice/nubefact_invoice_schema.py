from __future__ import annotations

REQUIRED_FIELDS = [
    "document_type",
    "series",
    "issue_date",
    "client_document_type",
    "client_document_number",
    "client_name",
    "client_address",
    "currency",
    "igv_percentage",
    "total_igv",
    "total",
]

ITEM_REQUIRED_FIELDS = [
    "uom",
    "item_code",
    "description",
    "quantity",
    "unit_price",
    "unit_price_with_tax",
    "line_total",
    "igv_type",
    "igv",
    "line_total_with_tax",
]

DELIVERY_REFERENCE_REQUIRED_FIELDS = ["guide_type", "guide_series_number"]

PAYMENT_INSTALLMENT_REQUIRED_FIELDS = ["installment_number", "payment_date", "amount"]

NOTE_REFERENCE_REQUIRED_FIELDS = [
    "base_document_type",
    "base_document_series",
    "base_document_number",
]

CREDIT_NOTE_REQUIRED_FIELDS = ["credit_note_reason"]
DEBIT_NOTE_REQUIRED_FIELDS = ["debit_note_reason"]
