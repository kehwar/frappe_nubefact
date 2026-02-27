# Canonical Model - NubeFact Frappe DocTypes

This document describes the Frappe DocTypes required for NubeFact API integration. These doctypes provide the canonical data model for managing electronic invoices, receipts, credit/debit notes, and delivery guides (guías de remisión).

---

## Current Implementation Status (as of 2026-02-27)

| Object | Status | Notes |
|--------|--------|-------|
| Nubefact Branch | ✅ Implemented | Active credentials container per branch/company. Uses `api_route` + `api_token`. |
| Nubefact API Log | ✅ Implemented | Request/response logging active. Uses `status` (`Success`/`Error`) and script-based naming from `request_timestamp`. |
| Request API Utility (`make_request`) | ✅ Implemented | Sends POST requests, handles errors, and writes API log entries. |
| Nubefact Delivery Note | ❌ Not Implemented | Canonical model only. |
| Nubefact Invoice | ❌ Not Implemented | Canonical model only. |

---

## 1. Nubefact Branch

**DocType Name**: `Nubefact Branch`
**Type**: Standard DocType
**Purpose**: Stores per-branch NubeFact API credentials and route.

### Current Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Title | `title` | Data | Yes | Human-friendly branch name. |
| Company | `company` | Link | No | Optional ERP company mapping. |
| API Route | `api_route` | Data | Yes | Client route appended to API base URL (or absolute URL). |
| API Token | `api_token` | Password | Yes | Authorization token used in request header. |

### Implementation Status
- ✅ Implemented
- Used directly by `get_request_config()` in API request flow.

---

## 2. Nubefact API Log

**DocType Name**: `Nubefact API Log`
**Type**: Standard DocType
**Purpose**: Logs all API requests and responses for auditing and troubleshooting.

### Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| **Request Details** | | Section Break | | |
| Operation | `operation` | Select | Yes | Options: generar_comprobante, consultar_comprobante, generar_anulacion, consultar_anulacion, generar_guia, consultar_guia |
| API Route | `api_route` | Data | No | Effective request route/URL used for API call |
| Reference DocType | `reference_doctype` | Link | No | DocType name of source document |
| Reference Name | `reference_name` | Dynamic Link | No | Name of source document |
| Request Timestamp | `request_timestamp` | Datetime | Yes | When the request was sent |
| Request Payload | `request_payload` | Code | No | Full JSON request payload |
| **Response Details** | | Section Break | | |
| Response Timestamp | `response_timestamp` | Datetime | No | When the response was received |
| Response Status Code | `response_status_code` | Int | No | HTTP status code |
| Response Payload | `response_payload` | Code | No | Full JSON response payload |
| Status | `status` | Select | No | Options: Success, Error |
| **Error Details** | | Section Break | | |
| Error Code | `error_code` | Data | No | NubeFact error code if failed |
| Error Message | `error_message` | Text | No | Error message if failed |
| Duration (ms) | `duration_ms` | Int | No | Request duration in milliseconds |

### Settings
- Auto Name: `By script` (generated from `request_timestamp`, with collision suffix when needed)
- Sort Field: `request_timestamp`
- Sort Order: DESC
- Track Changes: Disabled
- Allow Rename: No

### Status Colors
- Success: green
- Error: red

### Permissions
- System Manager: Full access
- Accounts Manager: Read only

### Implementation Status
- ✅ Implemented.
- `create_api_log(...)` is used by `make_request(...)` to persist all API attempts.

---

## 3. Nubefact Delivery Note

**DocType Name**: `Nubefact Delivery Note`
**Type**: Standard DocType
**Purpose**: Manages electronic delivery guides via NubeFact Guía de Remisión API.

### Supported Guide Types

- `7`: GRE Remitente (series must start with `T`)
- `8`: GRE Transportista (series must start with `V`)

### Implementation Priority

- ✅ First business implementation target (before `Nubefact Invoice`).

### Manual / Asset Alignment Notes

- Model aligned to `generar_guia` and `consultar_guia` examples in `assets/guia-remision-*`.
- Includes transport-specific arrays (`vehiculos_secundarios`, `conductores_secundarios`) and related documents (`documento_relacionado`).
- Includes post-acceptance output fields (`enlace_del_pdf`, `enlace_del_xml`, `enlace_del_cdr`, `cadena_para_codigo_qr`).

### Main Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| **Document Type** | | Section Break | | |
| Document Type | `document_type` | Data | Yes | 7 (GRE Remitente) or 8 (GRE Transportista) |
| Series | `series` | Data | Yes | 4-character series (`T*` for type 7, `V*` for type 8) |
| Number | `number` | Int | Yes | Sequential document number |
| | Column Break | | | |
| Issue Date | `issue_date` | Date | Yes | Date of guide issuance |
| Transfer Start Date | `transfer_start_date` | Date | Yes | When transport begins |
| **Client/Recipient Information** | | Section Break | | |
| Client Document Type | `client_document_type` | Select | Yes | Options: 6 (RUC), 1 (DNI), etc. |
| Client Document Number | `client_document_number` | Data | Yes | Client's identification number |
| Client Name | `client_name` | Data | Yes | Client's full name or business name |
| | Column Break | | | |
| Client Address | `client_address` | Small Text | Yes | Client's address |
| Client Email | `client_email` | Data | No | Primary client email |
| Client Email 1 | `client_email_1` | Data | No | Additional email address |
| Client Email 2 | `client_email_2` | Data | No | Additional email address |
| **Transportista Recipient (Type 8)** | | Section Break | | |
| Recipient Document Type | `recipient_document_type` | Select | No | Required for GRE Transportista |
| Recipient Document Number | `recipient_document_number` | Data | No | Required for GRE Transportista |
| Recipient Name | `recipient_name` | Data | No | Required for GRE Transportista |
| **Transfer Details** | | Section Break | | |
| Transfer Reason | `transfer_reason` | Select | Yes | SUNAT codes 01-19 |
| Transport Type | `transport_type` | Select | Yes | Options: 01 (Private), 02 (Public) |
| | Column Break | | | |
| Gross Total Weight | `gross_total_weight` | Float | Yes | Total weight |
| Weight Unit | `weight_unit` | Select | Yes | Options: KGM, TNE, etc. |
| Number of Packages | `number_of_packages` | Int | Yes | Total package count |
| **Carrier Information** | | Section Break | | |
| Carrier Document Type | `carrier_document_type` | Select | No | Required for private transport |
| Carrier Document Number | `carrier_document_number` | Data | No | Carrier's RUC/DNI |
| Carrier Name | `carrier_name` | Data | No | Carrier business name |
| | Column Break | | | |
| Vehicle License Plate | `vehicle_license_plate` | Data | No | Main vehicle plate |
| **Driver Information** | | Section Break | | |
| Driver Document Type | `driver_document_type` | Select | No | Usually 1 (DNI) |
| Driver Document Number | `driver_document_number` | Data | No | Driver's ID number |
| Driver First Name | `driver_first_name` | Data | No | Driver's given name |
| | Column Break | | | |
| Driver Last Name | `driver_last_name` | Data | No | Driver's family name |
| Driver License Number | `driver_license_number` | Data | No | Driver's license ID |
| **Origin (Punto de Partida)** | | Section Break | | |
| Origin Ubigeo | `origin_ubigeo` | Data | Yes | 6-digit SUNAT ubigeo code |
| Origin Address | `origin_address` | Small Text | Yes | Full origin address |
| | Column Break | | | |
| Origin Establishment Code | `origin_establishment_code` | Data | No | SUNAT establishment code (default "0000") |
| **Destination (Punto de Llegada)** | | Section Break | | |
| Destination Ubigeo | `destination_ubigeo` | Data | Yes | 6-digit SUNAT ubigeo code |
| Destination Address | `destination_address` | Small Text | Yes | Full destination address |
| | Column Break | | | |
| Destination Establishment Code | `destination_establishment_code` | Data | No | SUNAT establishment code (default "0000") |
| **Automation** | | Section Break | | |
| Auto Send to Client | `auto_send_to_client` | Check | No | Email PDF to client |
| PDF Format | `pdf_format` | Select | No | Options: "", "A4", "A5", "TICKET" |
| **Items** | | Section Break | | |
| Items | `items` | Table | Yes | Nubefact Delivery Item |
| **Related Documents** | | Section Break | | |
| Related Documents | `related_documents` | Table | No | Nubefact Delivery Related Document |
| **Secondary Vehicles** | | Section Break | | |
| Secondary Vehicles | `secondary_vehicles` | Table | No | Nubefact Delivery Secondary Vehicle |
| **Secondary Drivers** | | Section Break | | |
| Secondary Drivers | `secondary_drivers` | Table | No | Nubefact Delivery Secondary Driver |
| **Additional Information** | | Section Break | | |
| Observations | `observations` | Text | No | Additional notes |
| **SUNAT Status** | | Section Break | | |
| Accepted by SUNAT | `accepted_by_sunat` | Check | No | Whether guide was accepted |
| SUNAT Response Code | `sunat_response_code` | Data | No | SUNAT response code |
| SUNAT Response Message | `sunat_response_message` | Text | No | SUNAT response message |
| SUNAT Note | `sunat_note` | Text | No | Additional SUNAT note |
| SUNAT SOAP Error | `sunat_soap_error` | Text | No | SOAP error from SUNAT |
| | Column Break | | | |
| Link URL | `link_url` | Data | No | NubeFact link |
| CDR URL | `cdr_url` | Data | No | URL to download CDR |
| PDF URL | `pdf_url` | Data | No | URL to download PDF |
| XML URL | `xml_url` | Data | No | URL to download XML |
| QR URL | `qr_url` | Data | No | URL to QR code |

### Child Table: Nubefact Delivery Note Item

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Unit of Measure | `unit_of_measure` | Data | Yes | Unit code (e.g., NIU) |
| Item Code | `item_code` | Data | Yes | Internal product code |
| Description | `description` | Text | Yes | Product description |
| Quantity | `quantity` | Float | Yes | Item quantity |

### Child Table: Nubefact Delivery Note Related Document

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Document Type | `document_type` | Select | Yes | 01=Factura, 02=Boleta, etc. |
| Series | `series` | Data | Yes | Document series |
| Number | `number` | Data | Yes | Document number |

### Child Table: Nubefact Delivery Note Secondary Vehicle

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| License Plate | `license_plate` | Data | Yes | Vehicle license plate number |
| TUC | `tuc` | Data | No | Required for Transportista use cases |

### Child Table: Nubefact Delivery Note Secondary Driver

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Document Type | `document_type` | Select | Yes | Usually 1 (DNI) |
| Document Number | `document_number` | Data | Yes | Driver's ID number |
| First Name | `first_name` | Data | Yes | Driver's given name |
| Last Name | `last_name` | Data | Yes | Driver's family name |
| License Number | `license_number` | Data | Yes | Driver's license ID |

### Settings
- Auto Name: `format:{series}-{number}`
- Sort Field: `issue_date`
- Sort Order: DESC
- Track Changes: Yes
- Is Submittable: Yes

### Permissions
- Stock Manager: Full access (create, read, write, submit, cancel)
- Stock User: Create, Read, Write, Submit
- Sales User: Read only

### Implementation Status
- 🟡 In progress (DocType scaffold created).

---

## 4. Nubefact Invoice

**DocType Name**: `Nubefact Invoice`
**Type**: Standard DocType
**Purpose**: Manages electronic invoices, receipts (boletas), credit notes, and debit notes via NubeFact JSON v1 API.

### Main Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| **Document Type** | | Section Break | | |
| Document Type | `document_type` | Select | Yes | Options: 1 (Factura), 2 (Boleta), 3 (Nota de Crédito), 4 (Nota de Débito) |
| Series | `series` | Data | Yes | 4-character series (F* for Factura, B* for Boleta) |
| Number | `number` | Int | Yes | Sequential document number |
| SUNAT Transaction Type | `sunat_transaction` | Select | No | SUNAT transaction code (1-30+) |
| | Column Break | | | |
| Issue Date | `issue_date` | Date | Yes | Date of document issuance |
| Due Date | `due_date` | Date | No | Payment due date |
| **Client Information** | | Section Break | | |
| Client Document Type | `client_document_type` | Select | Yes | Options: 6 (RUC), 1 (DNI), 4 (Carnet), 7 (Passport), etc. |
| Client Document Number | `client_document_number` | Data | Yes | Client's identification number |
| Client Name | `client_name` | Data | Yes | Client's full name or business name |
| | Column Break | | | |
| Client Address | `client_address` | Small Text | Yes | Client's full address |
| Client Email | `client_email` | Data | No | Primary client email |
| Client Email 1 | `client_email_1` | Data | No | Additional email address |
| Client Email 2 | `client_email_2` | Data | No | Additional email address |
| **Currency and Exchange** | | Section Break | | |
| Currency | `currency` | Link | Yes | Link to Currency (1=PEN, 2=USD) |
| Exchange Rate | `exchange_rate` | Float | No | Required if currency = USD |
| | Column Break | | | |
| IGV Percentage | `igv_percentage` | Float | Yes | Default: 18.00 |
| **Amounts** | | Section Break | | |
| Total Taxable | `total_taxable` | Currency | No | Total gravada amount |
| Total Unaffected | `total_unaffected` | Currency | No | Total inafecta amount |
| Total Exempt | `total_exempt` | Currency | No | Total exonerada amount |
| Total IGV | `total_igv` | Currency | Yes | Total IGV/tax amount |
| | Column Break | | | |
| Global Discount | `global_discount` | Currency | No | Global discount amount |
| Total Discount | `total_discount` | Currency | No | Sum of all discounts |
| Total Advance | `total_advance` | Currency | No | Total advance payment |
| Total Free | `total_free` | Currency | No | Total complimentary amount |
| Total Other Charges | `total_other_charges` | Currency | No | Additional charges |
| | Column Break | | | |
| Total | `total` | Currency | Yes | Final total including taxes |
| **Perception and Retention** | | Section Break | | |
| Perception Type | `perception_type` | Data | No | SUNAT perception type code |
| Perception Base | `perception_base` | Currency | No | Taxable base for perception |
| Total Perception | `total_perception` | Currency | No | Perception amount |
| Total with Perception | `total_with_perception` | Currency | No | Grand total with perception |
| | Column Break | | | |
| Retention Type | `retention_type` | Data | No | SUNAT retention type code |
| Retention Base | `retention_base` | Currency | No | Taxable base for retention |
| Total Retention | `total_retention` | Currency | No | Retention amount |
| Total Plastic Bag Tax | `total_plastic_bag_tax` | Currency | No | Plastic bag tax (ICBPER) |
| **Detraction** | | Section Break | | |
| Subject to Detraction | `subject_to_detraction` | Check | No | Whether detraction applies |
| **Credit/Debit Note References** | | Section Break | | |
| Modifies Document Type | `modifies_document_type` | Select | No | Type of document being modified (1-4) |
| Modifies Series | `modifies_series` | Data | No | Series of document being modified |
| Modifies Number | `modifies_number` | Int | No | Number of document being modified |
| | Column Break | | | |
| Credit Note Reason | `credit_note_reason` | Select | No | SUNAT credit note reason (1-13) |
| Debit Note Reason | `debit_note_reason` | Select | No | SUNAT debit note reason (1-3) |
| **Payment and Delivery** | | Section Break | | |
| Payment Terms | `payment_terms` | Small Text | No | Payment conditions description |
| Payment Method | `payment_method` | Data | No | Payment method description |
| Vehicle License Plate | `vehicle_license_plate` | Data | No | Delivery vehicle plate |
| Purchase Order | `purchase_order` | Data | No | Client's PO/SO reference |
| | Column Break | | | |
| PDF Format | `pdf_format` | Select | No | Options: "", "A4", "A5", "TICKET" |
| Generated by Contingency | `generated_by_contingency` | Check | No | Contingency issuance flag |
| Goods from Jungle | `goods_from_jungle` | Check | No | Goods from jungle region |
| Services from Jungle | `services_from_jungle` | Check | No | Services from jungle region |
| **Automation** | | Section Break | | |
| Auto Send to SUNAT | `auto_send_to_sunat` | Check | No | Send immediately to SUNAT |
| Auto Send to Client | `auto_send_to_client` | Check | No | Email PDF to client |
| **Items** | | Section Break | | |
| Items | `items` | Table | Yes | Nubefact Invoice Item |
| **Related Guides** | | Section Break | | |
| Delivery Guides | `delivery_guides` | Table | No | Nubefact Invoice Delivery Reference |
| **Credit Sale** | | Section Break | | |
| Credit Sale Installments | `credit_installments` | Table | No | Nubefact Invoice Payment Installment |
| **Additional Information** | | Section Break | | |
| Observations | `observations` | Text | No | Additional notes |
| **SUNAT Status** | | Section Break | | |
| SUNAT Status | `sunat_status` | Select | No | Options: Pending, Accepted, Rejected, Voided |
| SUNAT Response Code | `sunat_response_code` | Data | No | SUNAT response code |
| SUNAT Response Message | `sunat_response_message` | Text | No | SUNAT response message |
| | Column Break | | | |
| CDR URL | `cdr_url` | Data | No | URL to download CDR |
| PDF URL | `pdf_url` | Data | No | URL to download PDF |
| XML URL | `xml_url` | Data | No | URL to download XML |
| **Void Information** | | Section Break | | |
| Voided | `voided` | Check | No | Whether document is voided |
| Void Date | `void_date` | Date | No | Date of void |
| Void Reason | `void_reason` | Small Text | No | Reason for voiding |
| | Column Break | | | |
| Void Status | `void_status` | Select | No | Options: Pending, Accepted, Rejected |
| Void Ticket | `void_ticket` | Data | No | SUNAT void ticket number |

### Child Table: Nubefact Invoice Item

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Unit of Measure | `unit_of_measure` | Link | Yes | Link to UOM |
| Item Code | `item_code` | Data | Yes | Internal product/service code |
| SUNAT Product Code | `sunat_product_code` | Data | No | 8-digit SUNAT catalog code |
| Description | `description` | Text | Yes | Product/service description |
| Quantity | `quantity` | Float | Yes | Item quantity |
| Unit Value | `unit_value` | Currency | Yes | Unit price without taxes |
| Unit Price | `unit_price` | Currency | Yes | Unit price including taxes |
| Discount | `discount` | Currency | No | Discount per item |
| Subtotal | `subtotal` | Currency | Yes | Line subtotal without taxes |
| IGV Type | `igv_type` | Select | Yes | 1=Gravada, 2=Exonerada, 3=Inafecta, etc. |
| IGV | `igv` | Currency | Yes | IGV amount for this line |
| Total | `total` | Currency | Yes | Line total including taxes |
| Advance Regularization | `advance_regularization` | Check | No | Is advance payment regularization |
| Advance Document Series | `advance_document_series` | Data | No | Advance document series |
| Advance Document Number | `advance_document_number` | Data | No | Advance document number |

### Child Table: Nubefact Invoice Delivery Reference

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Guide Type | `guide_type` | Select | Yes | SUNAT guide type code |
| Guide Series and Number | `guide_series_number` | Data | Yes | Format: "0001-23" |

### Child Table: Nubefact Invoice Payment Installment

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Installment Number | `installment_number` | Int | Yes | Installment sequence |
| Payment Date | `payment_date` | Date | Yes | Due date for installment |
| Amount | `amount` | Currency | Yes | Installment amount |

### Settings
- Auto Name: `format:{series}-{number}`
- Sort Field: `issue_date`
- Sort Order: DESC
- Track Changes: Yes
- Is Submittable: Yes

### Permissions
- Accounts Manager: Full access (create, read, write, submit, cancel)
- Accounts User: Create, Read, Write, Submit
- Sales User: Read only

### Implementation Status
- ❌ Not implemented in codebase yet (canonical target only).

---

## Implementation Notes

### Field Naming Conventions
- Use snake_case for field names (Frappe standard)
- Keep field names descriptive but concise
- Prefix child table fields with their context when needed

### Data Type Mappings

| API Type | Frappe Field Type | Notes |
|----------|------------------|-------|
| String (short) | Data | Max 140 characters |
| String (long) | Text or Small Text | Use Text for unlimited, Small Text for ~500 chars |
| Numeric (decimal) | Float or Currency | Use Currency for monetary values |
| Numeric (integer) | Int | For counters, quantities without decimals |
| Boolean | Check | Yes/No checkboxes |
| Date (DD-MM-YYYY) | Date | Frappe stores as YYYY-MM-DD, convert on API calls |
| Array of objects | Table | Child DocTypes |
| Select options | Select or Link | Use Link when referencing master data |

### Validation Requirements
1. **Series Validation**: Ensure series prefix matches document type (F* for Factura, B* for Boleta, T* for GRE Remitente, V* for GRE Transportista)
2. **Required Field Dependencies**: Many fields are conditionally required based on document type or other field values
3. **Numeric Totals**: Implement validation to ensure sum of items matches header totals
4. **SUNAT Integration**: Track submission status separately from document workflow status
5. **Date Logic**: Issue date cannot be in future; transfer start date must be >= issue date for guías

### API Integration Points
1. **On Submit**: Trigger `generar_comprobante` or `generar_guia` operation
2. **Status Polling**: Use `consultar_comprobante` or `consultar_guia` to check SUNAT acceptance
3. **Void/Cancel**: Trigger `generar_anulacion` operation
4. **Error Handling**: Log all API calls to Nubefact API Log for troubleshooting
