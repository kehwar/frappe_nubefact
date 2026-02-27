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

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| **Document** | | - | Section Break | | |
| Status | `status` | - | Select | No | `Draft`, `Pending Response`, `Accepted`, `Error`. Read-only, set by code. |
| Title | `title` | - | Data | No | Auto-generated read-only title. |
| Document Type | `document_type` | `tipo_de_comprobante` | Select | Yes* | `7` GRE REMITENTE, `8` GRE TRANSPORTISTA |
| Series | `series` | `serie` | Data | Yes* | Series value (T* for Remitente, V* for Transportista) |
| Number | `number` | `numero` | Int | No | Sequential document number. Optional on send; API response can assign/fill it. |
| | | - | Column Break | | |
| Issue Date | `issue_date` | `fecha_de_emision` | Date | Yes* | Date of guide issuance |
| Transfer Start Date | `transfer_start_date` | `fecha_de_inicio_de_traslado` | Date | Yes* | When transport begins |
| Branch | `branch` | - | Link | No | Nubefact Branch used for API calls. Auto-filled from last used. |
| **Client/Recipient Information** | | - | Section Break | | |
| Client Document Type | `client_document_type` | `cliente_tipo_de_documento` | Select | Yes* | `6` RUC, `1` DNI, `4` CARNET DE EXTRANJERÍA, `7` PASAPORTE, `A` CÉDULA DIPLOMÁTICA, `0` NO DOMICILIADO |
| Client Document Number | `client_document_number` | `cliente_numero_de_documento` | Data | Yes* | Client's identification number |
| Client Name | `client_name` | `cliente_denominacion` | Data | Yes* | Client's full name or business name |
| | | - | Column Break | | |
| Client Address | `client_address` | `cliente_direccion` | Small Text | Yes* | Client's full address |
| Client Email | `client_email` | `cliente_email` | Data | No | Primary client email |
| Client Email 1 | `client_email_1` | `cliente_email_1` | Data | No | Additional email address |
| Client Email 2 | `client_email_2` | `cliente_email_2` | Data | No | Additional email address |
| **GRE Transportista Recipient (Type 8)** | | - | Section Break | | |
| Recipient Document Type | `recipient_document_type` | `destinatario_documento_tipo` | Select | Yes* | Required when `document_type = 8`. `6` RUC, `1` DNI, `4` CARNET DE EXTRANJERÍA, `7` PASAPORTE, `A` CÉDULA DIPLOMÁTICA, `0` NO DOMICILIADO |
| Recipient Document Number | `recipient_document_number` | `destinatario_documento_numero` | Data | Yes* | Required when `document_type = 8`. |
| Recipient Name | `recipient_name` | `destinatario_denominacion` | Data | Yes* | Required when `document_type = 8`. |
| **Transfer Details** | | - | Section Break | | |
| Transfer Reason | `transfer_reason` | `motivo_de_traslado` | Select | Yes* | Required for type 7. `01` VENTA, `02` COMPRA, `03` VENTA CON ENTREGA A TERCEROS, `04` TRASLADO ENTRE ESTABLECIMIENTOS, `05` CONSIGNACION, `06` DEVOLUCION, `07` RECOJO DE BIENES TRANSFORMADOS, `08` IMPORTACION, `09` EXPORTACION, `13` OTROS, `14` VENTA SUJETA A CONFIRMACION, `17` TRASLADO BIENES PARA TRANSFORMACION, `18` TRASLADO EMISOR ITINERANTE CP |
| Transport Type | `transport_type` | `tipo_de_transporte` | Select | Yes* | Required for type 7. `01` TRANSPORTE PÚBLICO, `02` TRANSPORTE PRIVADO |
| Gross Total Weight | `gross_total_weight` | `peso_bruto_total` | Float | Yes* | Total weight in KGM or TNE |
| Weight Unit | `weight_unit` | `peso_bruto_unidad_de_medida` | Select | Yes* | `KGM` Kilogramos, `TNE` Toneladas |
| Number of Packages | `number_of_packages` | `numero_de_bultos` | Int | Yes* | Required for type 7. Total package count. |
| | | - | Column Break | | |
| Carrier Document Type | `carrier_document_type` | `transportista_documento_tipo` | Select | No | Required for type 7 public transport (`01`). `6` RUC |
| Carrier Document Number | `carrier_document_number` | `transportista_documento_numero` | Data | No | Required for type 7 public transport. Carrier's RUC |
| Carrier Name | `carrier_name` | `transportista_denominacion` | Data | No | Required for type 7 public transport. Carrier business name |
| Vehicle License Plate | `vehicle_license_plate` | `transportista_placa_numero` | Data | Yes* | Main vehicle plate (required for all guide types) |
| **Main Driver** | | - | Section Break | | |
| Driver Document Type | `driver_document_type` | `conductor_documento_tipo` | Select | No | Required for type 7 private transport and all type 8. `1` DNI, `4` CARNET DE EXTRANJERÍA, `7` PASAPORTE, `A` CÉDULA DIPLOMÁTICA, `0` NO DOMICILIADO |
| Driver Document Number | `driver_document_number` | `conductor_documento_numero` | Data | No | Required for type 7 private transport and all type 8. |
| Driver First Name | `driver_first_name` | `conductor_nombre` | Data | No | Required for type 7 private transport and all type 8. |
| | | - | Column Break | | |
| Driver Last Name | `driver_last_name` | `conductor_apellidos` | Data | No | Required for type 7 private transport and all type 8. |
| Driver License Number | `driver_license_number` | `conductor_numero_licencia` | Data | No | Required for type 7 private transport and all type 8. |
| **Origin / Destination** | | - | Section Break | | |
| Origin Ubigeo | `origin_ubigeo` | `punto_de_partida_ubigeo` | Data | Yes* | 6-digit SUNAT ubigeo code. Falls back to Branch ubigeo if blank. |
| Origin Address | `origin_address` | `punto_de_partida_direccion` | Small Text | Yes* | Full origin address. Falls back to Branch address if blank. |
| Origin SUNAT Code | `origin_sunat_code` | `punto_de_partida_codigo_establecimiento_sunat` | Data | No | SUNAT establishment code. Falls back to Branch sunat_code if blank. |
| | | - | Column Break | | |
| Destination Ubigeo | `destination_ubigeo` | `punto_de_llegada_ubigeo` | Data | Yes* | 6-digit SUNAT ubigeo code. |
| Destination Address | `destination_address` | `punto_de_llegada_direccion` | Small Text | Yes* | Full destination address. |
| Destination SUNAT Code | `destination_sunat_code` | `punto_de_llegada_codigo_establecimiento_sunat` | Data | No | SUNAT establishment code (default "0000") |
| **Items** | | - | Section Break | | |
| Items | `items` | `items` | Table | Yes* | Nubefact Delivery Note Item. At least one row required. |
| **Related Documents** | | - | Section Break | | |
| Related Documents | `related_documents` | `documento_relacionado` | Table | No | Nubefact Delivery Note Related Document |
| **Secondary Vehicles** | | - | Section Break | | |
| Secondary Vehicles | `secondary_vehicles` | `vehiculos_secundarios` | Table | No | Nubefact Delivery Note Secondary Vehicle |
| **Secondary Drivers** | | - | Section Break | | |
| Secondary Drivers | `secondary_drivers` | `conductores_secundarios` | Table | No | Nubefact Delivery Note Secondary Driver |
| **Additional Information** | | - | Section Break | | |
| Observations | `observations` | `observaciones` | Text | No | Additional notes |
| **More Information** | | - | Tab Break | | |
| **Settings** | | - | Section Break | | |
| Auto Send to Client | `auto_send_to_client` | `enviar_automaticamente_al_cliente` | Check | No | Email PDF to client |
| Skip Required Fields Validation | `skip_required_fields_validation` | - | Check | No | If enabled, bypasses server-side field validation in `validate()`. |
| PDF Format | `pdf_format` | `formato_de_pdf` | Select | No | `""` FORMATO POR DEFECTO, `A4` FORMATO A4, `TICKET` FORMATO TICKET |
| **SUNAT Status** | | - | Section Break | | |
| Accepted by SUNAT | `accepted_by_sunat` | `aceptada_por_sunat` | Check | No | Whether guide was accepted. Read-only. |
| Last SUNAT Check | `last_sunat_check` | - | Datetime | No | Timestamp of last consultar_guia call. Read-only. |
| SUNAT Response Code | `sunat_response_code` | `sunat_responsecode` | Data | No | SUNAT response code. Read-only. |
| SUNAT Response Message | `sunat_response_message` | `sunat_description` | Text | No | SUNAT response message. Read-only. |
| SUNAT Note | `sunat_note` | `sunat_note` | Text | No | Additional SUNAT note. Read-only. |
| SUNAT SOAP Error | `sunat_soap_error` | `sunat_soap_error` | Text | No | SOAP error from SUNAT. Read-only. |
| Error Message | `error_message` | - | Text | No | Last integration/send error summary. Read-only. |
| | | - | Column Break | | |
| Link URL | `link_url` | `enlace` | Data | No | NubeFact link. Read-only. |
| CDR URL | `cdr_url` | `enlace_del_cdr` | Data | No | URL to download CDR. Read-only. |
| PDF URL | `pdf_url` | `enlace_del_pdf` | Data | No | URL to download PDF. Read-only. |
| XML URL | `xml_url` | `enlace_del_xml` | Data | No | URL to download XML. Read-only. |
| QR URL | `qr_url` | `cadena_para_codigo_qr` | Data | No | URL to QR code string. Read-only. |

## Child Table: Nubefact Delivery Note Item

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| Unit of Measure | `unit_of_measure` | `unidad_de_medida` | Data | Yes | Unit code (e.g., NIU, ZZ) |
| Item Code | `item_code` | `codigo` | Data | No | Internal product code |
| Description | `description` | `descripcion` | Text | Yes | Product description |
| Quantity | `quantity` | `cantidad` | Float | Yes | Item quantity |

## Child Table: Nubefact Delivery Note Related Document

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| Document Type | `document_type` | `tipo` | Select | Yes | `01` Factura, `03` Boleta de Venta, `09` Guía de Remisión Remitente, `31` Guía de Remisión Transportista |
| Series | `series` | `serie` | Data | Yes | Document series |
| Number | `number` | `numero` | Data | Yes | Document number |

## Child Table: Nubefact Delivery Note Secondary Vehicle

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| License Plate | `license_plate` | `placa_numero` | Data | Yes | Vehicle license plate number |
| TUC | `tuc` | `tuc` | Data | No | Required for Transportista use cases |

## Child Table: Nubefact Delivery Note Secondary Driver

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| Document Type | `document_type` | `documento_tipo` | Select | Yes | `1` DNI, `4` CARNET DE EXTRANJERÍA, `7` PASAPORTE, `A` CÉDULA DIPLOMÁTICA, `0` NO DOMICILIADO |
| Document Number | `document_number` | `documento_numero` | Data | Yes | Driver's ID number |
| First Name | `first_name` | `nombre` | Data | Yes | Driver's given name |
| Last Name | `last_name` | `apellidos` | Data | Yes | Driver's family name |
| License Number | `license_number` | `numero_licencia` | Data | Yes | Driver's license ID |

## Select Values Legend

### Main DocType Selects

| Field Name | NubeFact Field | Legend |
|------------|----------------|--------|
| `document_type` | `tipo_de_comprobante` | `7` GRE REMITENTE, `8` GRE TRANSPORTISTA |
| `client_document_type` | `cliente_tipo_de_documento` | `6` RUC, `1` DNI, `4` CARNET DE EXTRANJERÍA, `7` PASAPORTE, `A` CÉDULA DIPLOMÁTICA DE IDENTIDAD, `0` NO DOMICILIADO |
| `transfer_reason` | `motivo_de_traslado` | `01` VENTA, `02` COMPRA, `03` VENTA CON ENTREGA A TERCEROS, `04` TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA, `05` CONSIGNACION, `06` DEVOLUCION, `07` RECOJO DE BIENES TRANSFORMADOS, `08` IMPORTACION, `09` EXPORTACION, `13` OTROS, `14` VENTA SUJETA A CONFIRMACION DEL COMPRADOR, `17` TRASLADO DE BIENES PARA TRANSFORMACION, `18` TRASLADO EMISOR ITINERANTE CP |
| `transport_type` | `tipo_de_transporte` | `01` TRANSPORTE PÚBLICO, `02` TRANSPORTE PRIVADO |
| `weight_unit` | `peso_bruto_unidad_de_medida` | `KGM` Kilogramos, `TNE` Toneladas |
| `pdf_format` | `formato_de_pdf` | `""` FORMATO POR DEFECTO DE NUBEFACT, `A4` FORMATO A4, `TICKET` FORMATO TICKET |
| `status` | - | `Draft`, `Pending Response`, `Accepted`, `Error` (estado interno del DocType) |

\* `Required = Yes*` means the field is not marked mandatory in DocType schema, but is required by runtime validation (`_validate_required_fields`) unless `skip_required_fields_validation` is enabled.

## Runtime Validation Groups (`nubefact_delivery_note_schema.py`)

| Constant | When Applied |
|----------|-------------|
| `REQUIRED_FIELDS` | Always — for all guide types |
| `TYPE_7_REQUIRED_FIELDS` | When `document_type = 7` (GRE Remitente) |
| `PUBLIC_TRANSPORT_REQUIRED_FIELDS` | When `document_type = 7` and `transport_type = "01"` |
| `DRIVER_REQUIRED_FIELDS` | When `document_type = 7` and `transport_type = "02"`, or when `document_type = 8` |
| `TYPE_8_RECIPIENT_REQUIRED_FIELDS` | When `document_type = 8` (GRE Transportista) |
| `ITEM_REQUIRED_FIELDS` | Per item row |
| `RELATED_DOCUMENT_REQUIRED_FIELDS` | Per related document row |
| `SECONDARY_VEHICLE_REQUIRED_FIELDS` | Per secondary vehicle row |
| `SECONDARY_DRIVER_REQUIRED_FIELDS` | Per secondary driver row |

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

