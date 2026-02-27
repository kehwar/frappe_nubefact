# DocType: Nubefact Delivery Note

**DocType Name**: `Nubefact Delivery Note`
**Type**: Standard DocType
**Purpose**: Manages electronic delivery guides via NubeFact Guía de Remisión API.

## Supported Guide Types

- `7`: GRE Remitente (series must start with `T`)
- `8`: GRE Transportista (series must start with `V`)

## Manual / Asset Alignment Notes

- Model aligned to `generar_guia` and `consultar_guia` examples in `assets/gre-example-*.json` (indexed in `references/gre-examples.md`).
- `number` / `numero` is optional on send. If omitted, NubeFact auto-generates the next sequential number.
- Includes transport-specific arrays (`vehiculos_secundarios`, `conductores_secundarios`) and related documents (`documento_relacionado`).
- Includes post-acceptance output fields (`enlace_del_pdf`, `enlace_del_xml`, `enlace_del_cdr`, `cadena_para_codigo_qr`).

## Main Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| **Document** | | Section Break | | |
| Status | `status` | Select | No | Options: Draft, Pending Response, Accepted, Error. Read-only, set by code. |
| Title | `title` | Data | No | Auto-generated read-only title. |
| Document Type | `document_type` | Select | Yes* | 7 (GRE Remitente) or 8 (GRE Transportista). |
| Series | `series` | Data | Yes* | Series value. |
| Number | `number` | Int | No | Sequential document number. Optional on send; API response can assign/fill it. |
| | Column Break | | | |
| Issue Date | `issue_date` | Date | No | Date of guide issuance |
| Transfer Start Date | `transfer_start_date` | Date | No | When transport begins |
| Branch | `branch` | Link | No | Nubefact Branch used for API calls. Auto-filled from last used. |
| **Client/Recipient Information** | | Section Break | | |
| Client Document Type | `client_document_type` | Select | Yes* | Options: 6, 1, 4, 7, A, 0. |
| Client Document Number | `client_document_number` | Data | Yes* | Client's identification number. |
| Client Name | `client_name` | Data | Yes* | Client's full name or business name. |
| | Column Break | | | |
| Client Address | `client_address` | Small Text | No | Client's address |
| Client Email | `client_email` | Data | No | Primary client email |
| Client Email 1 | `client_email_1` | Data | No | Additional email address |
| Client Email 2 | `client_email_2` | Data | No | Additional email address |
| **Transportista Recipient (Type 8)** | | Section Break | | |
| Recipient Document Type | `recipient_document_type` | Select | Yes* | Required when `document_type = 8`. |
| Recipient Document Number | `recipient_document_number` | Data | Yes* | Required when `document_type = 8`. |
| Recipient Name | `recipient_name` | Data | Yes* | Required when `document_type = 8`. |
| **Transfer Details** | | Section Break | | |
| Transfer Reason | `transfer_reason` | Select | Yes* | SUNAT codes 01, 02, 04, 05, 06, 07, 08, 09, 13, 14, 18, 19. |
| Transport Type | `transport_type` | Select | Yes* | Options: 01 (Private), 02 (Public). |
| Gross Total Weight | `gross_total_weight` | Float | Yes* | Total weight. |
| Weight Unit | `weight_unit` | Select | Yes* | Options: KGM, TNE. |
| Number of Packages | `number_of_packages` | Int | Yes* | Total package count. |
| | Column Break | | | |
| Carrier Document Type | `carrier_document_type` | Select | No | Required for private transport |
| Carrier Document Number | `carrier_document_number` | Data | No | Carrier's RUC/DNI |
| Carrier Name | `carrier_name` | Data | No | Carrier business name |
| Vehicle License Plate | `vehicle_license_plate` | Data | No | Main vehicle plate |
| **Main Driver** | | Section Break | | |
| Driver Document Type | `driver_document_type` | Select | No | Usually 1 (DNI) |
| Driver Document Number | `driver_document_number` | Data | No | Driver's ID number |
| Driver First Name | `driver_first_name` | Data | No | Driver's given name |
| | Column Break | | | |
| Driver Last Name | `driver_last_name` | Data | No | Driver's family name |
| Driver License Number | `driver_license_number` | Data | No | Driver's license ID |
| **Origin / Destination** | | Section Break | | |
| Origin Ubigeo | `origin_ubigeo` | Data | Yes* | 6-digit SUNAT ubigeo code. Falls back to Branch ubigeo if blank. |
| Origin Address | `origin_address` | Small Text | Yes* | Full origin address. Falls back to Branch address if blank. |
| Origin SUNAT Code | `origin_sunat_code` | Data | No | SUNAT establishment code. Falls back to Branch sunat_code if blank. |
| | Column Break | | | |
| Destination Ubigeo | `destination_ubigeo` | Data | Yes* | 6-digit SUNAT ubigeo code. |
| Destination Address | `destination_address` | Small Text | Yes* | Full destination address. |
| Destination SUNAT Code | `destination_sunat_code` | Data | No | SUNAT establishment code (default "0000") |
| **Items** | | Section Break | | |
| Items | `items` | Table | Yes* | Nubefact Delivery Note Item. At least one row required. |
| **Related Documents** | | Section Break | | |
| Related Documents | `related_documents` | Table | No | Nubefact Delivery Note Related Document |
| **Secondary Vehicles** | | Section Break | | |
| Secondary Vehicles | `secondary_vehicles` | Table | No | Nubefact Delivery Note Secondary Vehicle |
| **Secondary Drivers** | | Section Break | | |
| Secondary Drivers | `secondary_drivers` | Table | No | Nubefact Delivery Note Secondary Driver |
| **Additional Information** | | Section Break | | |
| Observations | `observations` | Text | No | Additional notes |
| **More Information** | | Tab Break | | |
| **Settings** | | Section Break | | |
| Auto Send to Client | `auto_send_to_client` | Check | No | Email PDF to client |
| Skip Required Fields Validation | `skip_required_fields_validation` | Check | No | If enabled, bypasses server-side field validation in `validate()`. |
| PDF Format | `pdf_format` | Select | No | Options: "", "A4", "A5", "TICKET" |
| **SUNAT Status** | | Section Break | | |
| Accepted by SUNAT | `accepted_by_sunat` | Check | No | Whether guide was accepted. Read-only. |
| Last SUNAT Check | `last_sunat_check` | Datetime | No | Timestamp of last consultar_guia call. Read-only. |
| SUNAT Response Code | `sunat_response_code` | Data | No | SUNAT response code. Read-only. |
| SUNAT Response Message | `sunat_response_message` | Text | No | SUNAT response message. Read-only. |
| SUNAT Note | `sunat_note` | Text | No | Additional SUNAT note. Read-only. |
| SUNAT SOAP Error | `sunat_soap_error` | Text | No | SOAP error from SUNAT. Read-only. |
| Error Message | `error_message` | Text | No | Last integration/send error summary. Read-only. |
| | Column Break | | | |
| Link URL | `link_url` | Data | No | NubeFact link. Read-only. |
| CDR URL | `cdr_url` | Data | No | URL to download CDR. Read-only. |
| PDF URL | `pdf_url` | Data | No | URL to download PDF. Read-only. |
| XML URL | `xml_url` | Data | No | URL to download XML. Read-only. |
| QR URL | `qr_url` | Data | No | URL to QR code string. Read-only. |

## Child Table: Nubefact Delivery Note Item

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Unit of Measure | `unit_of_measure` | Data | Yes | Unit code (e.g., NIU) |
| Item Code | `item_code` | Data | Yes | Internal product code |
| Description | `description` | Text | Yes | Product description |
| Quantity | `quantity` | Float | Yes | Item quantity |

## Child Table: Nubefact Delivery Note Related Document

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Document Type | `document_type` | Select | Yes | 01=Factura, 02=Boleta, etc. |
| Series | `series` | Data | Yes | Document series |
| Number | `number` | Data | Yes | Document number |

## Child Table: Nubefact Delivery Note Secondary Vehicle

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| License Plate | `license_plate` | Data | Yes | Vehicle license plate number |
| TUC | `tuc` | Data | No | Required for Transportista use cases |

## Child Table: Nubefact Delivery Note Secondary Driver

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Document Type | `document_type` | Select | Yes | Usually 1 (DNI) |
| Document Number | `document_number` | Data | Yes | Driver's ID number |
| First Name | `first_name` | Data | Yes | Driver's given name |
| Last Name | `last_name` | Data | Yes | Driver's family name |
| License Number | `license_number` | Data | Yes | Driver's license ID |

\* `Required = Yes*` means the field is not marked mandatory in DocType schema, but is required by runtime validation (`_validate_required_fields`) unless `skip_required_fields_validation` is enabled.

## Settings
- Auto Name: `By script` (timestamp-based, e.g. `20260227-123456-000001`)
- Sort Field: `modified`
- Sort Order: DESC
- Allow Rename: Yes

## Permissions
- System Manager: Full access

## Implementation Status
- ✅ Implemented.
- `send_to_nubefact(name)` — builds the `generar_guia` payload, calls the API, updates fields from response.
- `refresh_sunat_status(name)` — calls `consultar_guia`, updates SUNAT status fields.
- `poll_pending_delivery_notes()` — scheduled task that polls pending delivery notes every 5 minutes.
- `create_delivery_note_from_import_file(file_name)` — creates delivery note from uploaded file (JSON/XML input flows).
- `create_delivery_note_from_import_json_text(json_payload)` — creates delivery note directly from raw JSON payload.
- Origin fields (`origin_ubigeo`, `origin_address`, `origin_sunat_code`) fall back to Branch values if blank on the document.
