from __future__ import annotations

SUBMIT_REQUIRED_FIELDS = [
    "document_type",
    "series",
    "issue_date",
    "client_document_type",
    "client_document_number",
    "client_name",
    "client_address",
    "currency",
    "total_igv",
    "total",
]

ITEM_REQUIRED_FIELDS = [
    "unit_of_measure",
    "item_code",
    "description",
    "quantity",
    "unit_value",
    "unit_price",
    "subtotal",
    "igv_type",
    "igv",
    "total",
]

DELIVERY_REFERENCE_REQUIRED_FIELDS = ["guide_type", "guide_series_number"]

PAYMENT_INSTALLMENT_REQUIRED_FIELDS = ["installment_number", "payment_date", "amount"]

NOTE_REFERENCE_REQUIRED_FIELDS = [
    "modifies_document_type",
    "modifies_series",
    "modifies_number",
]

CREDIT_NOTE_REQUIRED_FIELDS = ["credit_note_reason"]
DEBIT_NOTE_REQUIRED_FIELDS = ["debit_note_reason"]
