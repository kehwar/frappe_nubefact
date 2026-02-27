from __future__ import annotations

SUBMIT_REQUIRED_FIELDS = [
    "document_type",
    "series",
    "client_document_type",
    "client_document_number",
    "client_name",
    "transfer_reason",
    "transport_type",
    "gross_total_weight",
    "weight_unit",
    "number_of_packages",
    "destination_ubigeo",
    "destination_address",
]
ITEM_REQUIRED_FIELDS = ["unit_of_measure", "item_code", "description", "quantity"]
RELATED_DOCUMENT_REQUIRED_FIELDS = ["document_type", "series", "number"]
SECONDARY_VEHICLE_REQUIRED_FIELDS = ["license_plate"]
SECONDARY_DRIVER_REQUIRED_FIELDS = [
    "document_type",
    "document_number",
    "first_name",
    "last_name",
    "license_number",
]
TYPE_8_RECIPIENT_REQUIRED_FIELDS = [
    "recipient_document_type",
    "recipient_document_number",
    "recipient_name",
]
