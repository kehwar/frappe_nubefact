# NubeFact Guía de Remisión API v1 - API Manual

**Reference**: [Google Docs - Guía de Remisión](https://docs.google.com/document/d/1vUpZrBEGJJRGpbUxFdKo2dBKSPfGRnLo2SINwgGSKoA/edit)
**PDF Source**: `assets/nubefact_guia_de_remision_v1.pdf`

This manual documents the NubeFact Guía de Remisión API for generating electronic delivery guides (GRE - Guía de Remisión Electrónica) with SUNAT (Peru).

---

## API Overview

The Guía de Remisión API provides REST endpoints for generating and querying electronic delivery guides. Unlike regular invoices, delivery guides require **SUNAT acceptance** before PDF, XML, and CDR artifacts are available.

### Base URL
```
https://api.nubefact.com/api/v1/<client-route>
```

### Authentication
All requests require an authorization header:
- `Authorization`: Your API authentication token

The `<client-route>` value is part of the URL path and identifies your assigned route.

### Request Format
- Method: `POST`
- Content-Type: `application/json`
- Header: `Authorization: <token>`
- Body: JSON payload with operation-specific fields

### Response Format
- Success: HTTP 200 with JSON response
- Error: JSON object with `errors` and `codigo`

---

## Document Types

### tipo_de_comprobante Values

| Code | Type | Series Prefix | Description |
|------|------|---------------|-------------|
| 7 | GRE Remitente | T* | Shipper's delivery guide |
| 8 | GRE Transportista | V* | Carrier's delivery guide |

---

## Operations

### 1. generar_guia

**Purpose**: Generate a new electronic delivery guide (GRE).

**Endpoint**: `POST /api/v1/<client-route>`

#### GRE Remitente (tipo 7)

**Request Example**: See [`guia-remision-generar-guia-remitente-request.json`](../assets/guia-remision-generar-guia-remitente-request.json) and [`guia-remision-generar-guia-remitente-request.jsonc`](../assets/guia-remision-generar-guia-remitente-request.jsonc)

**Key Request Fields**:
- `operacion`: Always "generar_guia"
- `tipo_de_comprobante`: 7 for GRE Remitente
- `serie`: 4-character series starting with "T" (e.g., "TTT1", "T001")
- `numero`: Sequential guide number
- `cliente_*`: Recipient identification and contact details
- `fecha_de_emision`: Issue date (DD-MM-YYYY)
- `fecha_de_inicio_de_traslado`: Transfer start date (DD-MM-YYYY)
- `motivo_de_traslado`: Transfer reason code (01-18)
- `tipo_de_transporte`: "01" (Private) or "02" (Public)
- `peso_bruto_total`: Total gross weight
- `peso_bruto_unidad_de_medida`: Weight unit (KGM, TNE, etc.)
- `numero_de_bultos`: Number of packages
- `punto_de_partida_*`: Origin location (ubigeo, address, establishment)
- `punto_de_llegada_*`: Destination location (ubigeo, address, establishment)
- `items[]`: Array of goods being transported

**Transport-Specific Fields**:

For **Private Transport** (`tipo_de_transporte: "01"`):
- `transportista_documento_tipo`: Carrier document type (usually "6" for RUC)
- `transportista_documento_numero`: Carrier RUC/document number
- `transportista_denominacion`: Carrier business name
- `transportista_placa_numero`: Main vehicle license plate
- `conductor_*`: Driver information (document type, number, name, license)
- `vehiculos_secundarios[]`: Additional vehicles (license plates only)
- `conductores_secundarios[]`: Additional drivers

For **Public Transport** (`tipo_de_transporte: "02"`):
- Public transport carrier information handled differently

**Related Documents**:
- `documento_relacionado[]`: Array of invoices/receipts related to this shipment
  - Each with `tipo`, `serie`, `numero`

**Response Example**: See [`guia-remision-generar-guia-remitente-response.json`](../assets/guia-remision-generar-guia-remitente-response.json) and [`guia-remision-generar-guia-remitente-response.jsonc`](../assets/guia-remision-generar-guia-remitente-response.jsonc)

**Initial Response Fields**:
- `nota_importante`: Important message about SUNAT acceptance requirement
- `tipo_de_comprobante`: 7 (echoed back)
- `serie`: Guide series (echoed back)
- `numero`: Guide number (echoed back)
- `enlace`: Empty initially (populated after SUNAT acceptance)
- `aceptada_por_sunat`: `false` (initially, until SUNAT accepts)
- `sunat_description`: `null` (until processed)
- `sunat_responsecode`: `null` (until processed)
- `pdf_zip_base64`: Empty (until SUNAT acceptance)
- `xml_zip_base64`: Empty (until SUNAT acceptance)
- `cdr_zip_base64`: Empty (until SUNAT acceptance)
- `cadena_para_codigo_qr`: Empty (until SUNAT acceptance)
- `enlace_del_pdf`: Empty (until SUNAT acceptance)
- `enlace_del_xml`: Empty (until SUNAT acceptance)
- `enlace_del_cdr`: Empty (until SUNAT acceptance)

---

#### GRE Transportista (tipo 8)

**Request Example**: See [`guia-remision-generar-guia-transportista-request.json`](../assets/guia-remision-generar-guia-transportista-request.json) and [`guia-remision-generar-guia-transportista-request.jsonc`](../assets/guia-remision-generar-guia-transportista-request.jsonc)

**Key Differences from Remitente**:
- `tipo_de_comprobante`: 8 for GRE Transportista
- `serie`: 4-character series starting with "V" (e.g., "VVV1", "V001")
- `destinatario_*`: Required recipient information fields
  - `destinatario_documento_tipo`
  - `destinatario_documento_numero`
  - `destinatario_denominacion`
- `transportista_placa_numero`: Main vehicle plate (transporter's vehicle)
- `conductor_*`: Driver information for transporter
- `vehiculos_secundarios[]`: Must include `tuc` (Transport Unique Code) field
  - Each vehicle: `placa_numero` and `tuc`

**Response Example**: See [`guia-remision-generar-guia-transportista-response.json`](../assets/guia-remision-generar-guia-transportista-response.json) and [`guia-remision-generar-guia-transportista-response.jsonc`](../assets/guia-remision-generar-guia-transportista-response.jsonc)

---

### 2. consultar_guia

**Purpose**: Query the status and retrieve artifacts of a previously generated guide.

**Endpoint**: `POST /api/v1/<client-route>`

**Request Example**: See [`guia-remision-consultar-guia-request.json`](../assets/guia-remision-consultar-guia-request.json) and [`guia-remision-consultar-guia-request.jsonc`](../assets/guia-remision-consultar-guia-request.jsonc)

**Request Fields**:
- `operacion`: Always "consultar_guia"
- `tipo_de_comprobante`: 7 (Remitente) or 8 (Transportista)
- `serie`: Guide series
- `numero`: Guide number (string format)

**Response Example**: See [`guia-remision-consultar-guia-response.json`](../assets/guia-remision-consultar-guia-response.json) and [`guia-remision-consultar-guia-response.jsonc`](../assets/guia-remision-consultar-guia-response.jsonc)

**Response Fields (After Acceptance)**:
- `aceptada_por_sunat`: `true` (when accepted)
- `enlace`: NubeFact URL to view guide
- `cadena_para_codigo_qr`: SUNAT QR code URL (e.g., https://e-factura.sunat.gob.pe/v1/contribuyente/gre/comprobantes/descargaqr?hashqr=...)
- `enlace_del_pdf`: URL to download PDF
- `enlace_del_xml`: URL to download XML
- `enlace_del_cdr`: URL to download CDR
- `pdf_zip_base64`: May be `null` if URLs are provided
- `xml_zip_base64`: May be `null` if URLs are provided
- `cdr_zip_base64`: May be `null` if URLs are provided

---

## Transfer Reason Codes

### motivo_de_traslado Values (GRE Remitente)

| Code | Description |
|------|-------------|
| 01 | Sale |
| 02 | Purchase |
| 04 | Consignment trade |
| 05 | Consignment |
| 06 | Import |
| 07 | Export |
| 08 | Sale with delivery to third party |
| 09 | Transfer between establishments of the same company |
| 13 | Others |
| 14 | Sale subject to confirmation by buyer |
| 18 | Transfer issuer ITINERANT CP |
| 19 | Transfer to primary production zone |

---

## Ubigeo Codes

SUNAT requires 6-digit ubigeo codes for origin and destination locations.

**Format**: `DDPPDD`
- DD: Department code (2 digits)
- PP: Province code (2 digits)
- DD: District code (2 digits)

**Examples**:
- `150101`: Lima / Lima / Lima
- `151021`: Lima / Callao / Bellavista
- `211101`: Puno / Puno / Puno

Refer to SUNAT's official ubigeo catalog for complete list.

---

## Related Document Types

### documento_relacionado tipo Values

| Code | Description |
|------|-------------|
| 01 | Factura |
| 02 | Boleta de Venta |
| 03 | Nota de Crédito |
| 04 | Nota de Débito |
| 06 | Carta de Porte Aéreo |
| 09 | Guía de Remisión Remitente |
| 12 | Ticket de Máquina Registradora |
| 31 | Guía de Remisión Transportista |
| 50 | DUA (Declaración Única de Aduanas) |
| 80 | Comprobante no emitido |

---

## Two-Step Workflow

### Critical Difference from JSON v1 API

Unlike invoices (JSON v1 API), delivery guides follow a **two-step asynchronous workflow**:

1. **Step 1: Generate Guide** (`generar_guia`)
   - Send guide data to NubeFact
   - NubeFact forwards to SUNAT for validation
   - Response returns immediately with minimal data
   - `aceptada_por_sunat` will be `false`
   - PDF, XML, CDR URLs will be empty

2. **Step 2: Poll for Acceptance** (`consultar_guia`)
   - Poll every 30-60 seconds
   - Check `aceptada_por_sunat` field
   - When `true`, retrieve PDF, XML, CDR URLs
   - QR code URL becomes available for display/printing

### Polling Strategy

```
DO:
  response = consultar_guia(serie, numero)
  IF response.aceptada_por_sunat == true:
    BREAK
  WAIT 30-60 seconds
WHILE (max 50 iterations OR 30 minutes)

IF response.aceptada_por_sunat == true:
  save_artifacts(response.enlace_del_pdf, response.enlace_del_xml, response.enlace_del_cdr)
  save_qr_url(response.cadena_para_codigo_qr)
ELSE:
  handle_timeout_or_rejection()
```

---

## Field Validations

### Series Naming
- **Remitente**: 4 characters starting with "T" (uppercase)
- **Transportista**: 4 characters starting with "V" (uppercase)

### Date Rules
- `fecha_de_emision`: Cannot be in the future
- `fecha_de_inicio_de_traslado`: Must be >= `fecha_de_emision`

### Weight and Packages
- `peso_bruto_total`: Must be > 0
- `numero_de_bultos`: Must be >= 1

### Establishment Codes
- If no specific establishment, use `"0000"` for `punto_de_partida_codigo_establecimiento_sunat` and `punto_de_llegada_codigo_establecimiento_sunat`

### License Plates
- Format: 3 letters + 3 digits (e.g., "ABC444") or similar patterns
- No special characters except hyphens

### TUC (Transport Unique Code) - Transportista Only
- Required for secondary vehicles in GRE Transportista
- Alphanumeric code assigned by transport regulatory authority

---

## Best Practices

### 1. Async Handling
- **Never** assume guide is ready immediately after `generar_guia`
- Always implement polling with `consultar_guia`
- Set reasonable timeout (e.g., 30 minutes)
- Handle both acceptance and rejection scenarios

### 2. Error Handling
- SUNAT rejection may not occur immediately
- Check `sunat_responsecode` and `sunat_description` for rejection reasons
- Log all responses for troubleshooting

### 3. QR Code Display
- QR code URL is only available after SUNAT acceptance
- Display QR on printed guides for verification
- QR links to official SUNAT verification page

### 4. Related Documents
- Always link delivery guides to source invoices/receipts
- Use `documento_relacionado[]` to establish traceability
- Required for SUNAT audit trail

### 5. Driver and Vehicle Management
- Maintain accurate driver license numbers
- Keep vehicle plates up to date
- For Transportista: Ensure TUC codes are current

### 6. Testing
- Test both Remitente and Transportista flows
- Verify private and public transport scenarios
- Test polling timeout handling
- Validate ubigeo codes against SUNAT catalog

---

## Common Errors

### Format Errors
- Incorrect series prefix (T* vs V*)
- Invalid ubigeo codes
- Missing required fields based on `tipo_de_transporte`
- Invalid date formats (must be DD-MM-YYYY)

### Business Logic Errors
- Transfer start date before issue date
- Invalid `motivo_de_traslado` code
- Missing driver info for private transport
- Missing TUC for Transportista secondary vehicles
- Missing destinatario for Transportista

### SUNAT Errors
- RUC not registered for GRE
- Invalid vehicle registration
- Driver license not found in SUNAT database
- Ubigeo code not in catalog

---

## Integration Checklist

- [ ] Implement two-step workflow (generate → poll)
- [ ] Handle SUNAT acceptance polling with timeouts
- [ ] Store QR code URL for guide verification
- [ ] Validate ubigeo codes before submission
- [ ] Distinguish between Remitente and Transportista requirements
- [ ] Implement transport type-specific field validation
- [ ] Link guides to source invoices via `documento_relacionado`
- [ ] Test rejection scenarios and error handling
- [ ] Store all artifact URLs (PDF, XML, CDR)
- [ ] Handle series naming rules (T* vs V*)
- [ ] Implement retry logic for network failures only
- [ ] Log all API interactions for audit

---

## Comparison: Remitente vs Transportista

| Aspect | GRE Remitente (tipo 7) | GRE Transportista (tipo 8) |
|--------|------------------------|----------------------------|
| **Used by** | Goods owner/shipper | Carrier/transport company |
| **Series** | T* prefix | V* prefix |
| **Transfer reason** | Required (`motivo_de_traslado`) | Not typically used |
| **Recipient** | Client info (`cliente_*`) | Separate destinatario fields required |
| **Transport type** | 01 (Private) or 02 (Public) | Usually own vehicles |
| **TUC codes** | Not required | Required for secondary vehicles |
| **Typical scenario** | Company shipping sold goods to customer | Transport company delivering for third party |

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
