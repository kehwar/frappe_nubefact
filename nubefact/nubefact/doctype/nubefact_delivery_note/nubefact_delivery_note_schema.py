from __future__ import annotations

# Required for all GRE guides (type 7 and type 8)
REQUIRED_FIELDS = [
    "document_type",
    "series",
    "issue_date",
    "client_document_type",
    "client_document_number",
    "client_name",
    "client_address",
    "gross_total_weight",
    "weight_unit",
    "transfer_start_date",
    "vehicle_license_plate",
    "origin_ubigeo",
    "origin_address",
    "destination_ubigeo",
    "destination_address",
]

# Required only for GRE Remitente (type 7)
TYPE_7_REQUIRED_FIELDS = [
    "transfer_reason",
    "transport_type",
    "number_of_packages",
]

# Required for GRE Remitente with public transport (transport_type = "01")
PUBLIC_TRANSPORT_REQUIRED_FIELDS = [
    "carrier_document_type",
    "carrier_document_number",
    "carrier_name",
]

# Required for GRE Remitente with private transport (transport_type = "02") and for all GRE Transportista (type 8)
DRIVER_REQUIRED_FIELDS = [
    "driver_document_type",
    "driver_document_number",
    "driver_first_name",
    "driver_last_name",
    "driver_license_number",
]

# Required only for GRE Transportista (type 8)
TYPE_8_RECIPIENT_REQUIRED_FIELDS = [
    "recipient_document_type",
    "recipient_document_number",
    "recipient_name",
]

ITEM_REQUIRED_FIELDS = ["unit_of_measure", "description", "quantity"]

RELATED_DOCUMENT_REQUIRED_FIELDS = ["document_type", "series", "number"]

SECONDARY_VEHICLE_REQUIRED_FIELDS = ["license_plate"]

SECONDARY_DRIVER_REQUIRED_FIELDS = [
    "document_type",
    "document_number",
    "first_name",
    "last_name",
    "license_number",
]
