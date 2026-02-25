# NubeFact JSON API v1 - API Manual

**Reference**: [Google Docs - Guía de Integración JSON v1](https://docs.google.com/document/d/1OosuF6j0pS0nU-qsGLuhQwqKbojbkTyXLFyC7CVVV7c/edit)
**PDF Source**: `assets/nubefact_api_json_v1.pdf`

This manual documents the NubeFact JSON API v1 for electronic invoicing with SUNAT (Peru).

---

## API Overview

The NubeFact JSON API provides a REST interface for generating, querying, and voiding electronic invoices, receipts (boletas), credit notes, and debit notes.

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
- Error: JSON object with `errors` (message) and `codigo` (error code)

---

## Operations

### 1. generar_comprobante

**Purpose**: Generate a new electronic invoice, receipt, credit note, or debit note.

**Endpoint**: `POST /api/v1/<client-route>`

**Request Example**: See [`json-v1-generar-comprobante-request.json`](../assets/json-v1-generar-comprobante-request.json) and [`json-v1-generar-comprobante-request.jsonc`](../assets/json-v1-generar-comprobante-request.jsonc) for detailed field descriptions.

**Key Request Fields**:
- `operacion`: Always "generar_comprobante"
- `tipo_de_comprobante`: 1 (Factura), 2 (Boleta), 3 (Nota de Crédito), 4 (Nota de Débito)
- `serie`: 4-character series code
- `numero`: Sequential document number
- `cliente_*`: Client identification and contact details
- `fecha_de_emision`: Issue date (DD-MM-YYYY format)
- `moneda`: 1 (PEN - Soles), 2 (USD - Dólares)
- `total_*`: Amount totals (taxable, IGV, final total, etc.)
- `items[]`: Array of line items with product/service details
- `enviar_automaticamente_a_la_sunat`: Boolean to auto-submit to SUNAT
- `enviar_automaticamente_al_cliente`: Boolean to auto-email PDF to client

**Special Fields**:

For **Credit/Debit Notes**:
- `documento_que_se_modifica_tipo`: Type of document being modified
- `documento_que_se_modifica_serie`: Series of document being modified
- `documento_que_se_modifica_numero`: Number of document being modified
- `tipo_de_nota_de_credito`: Reason code for credit note (1-13)
- `tipo_de_nota_de_debito`: Reason code for debit note (1-3)

For **Credit Sales**:
- `venta_al_credito[]`: Array of payment installments with `cuota`, `fecha_de_pago`, `importe`

For **Related Delivery Guides**:
- `guias[]`: Array of related guides with `guia_tipo`, `guia_serie_numero`

**Response Example**: See [`json-v1-generar-comprobante-response.json`](../assets/json-v1-generar-comprobante-response.json) and [`json-v1-generar-comprobante-response.jsonc`](../assets/json-v1-generar-comprobante-response.jsonc)

**Response Fields**:
- `aceptada_por_sunat`: Boolean - whether SUNAT accepted the document
- `sunat_description`: Human-readable SUNAT status message
- `sunat_responsecode`: "0" = accepted, other codes indicate errors
- `enlace`: URL to view document on NubeFact
- `enlace_del_pdf`: URL to download PDF
- `enlace_del_xml`: URL to download XML
- `enlace_del_cdr`: URL to download CDR (Constancia de Recepción)
- `cadena_para_codigo_qr`: String for generating QR code
- `codigo_hash`: Digital signature hash

---

### 2. consultar_comprobante

**Purpose**: Query the status and details of a previously generated document.

**Endpoint**: `POST /api/v1/<client-route>`

**Request Example**: See [`json-v1-consultar-comprobante-request.json`](../assets/json-v1-consultar-comprobante-request.json) and [`json-v1-consultar-comprobante-request.jsonc`](../assets/json-v1-consultar-comprobante-request.jsonc)

**Request Fields**:
- `operacion`: Always "consultar_comprobante"
- `tipo_de_comprobante`: Document type (1-4)
- `serie`: Document series
- `numero`: Document number

**Response Example**: See [`json-v1-consultar-comprobante-response.json`](../assets/json-v1-consultar-comprobante-response.json) and [`json-v1-consultar-comprobante-response.jsonc`](../assets/json-v1-consultar-comprobante-response.jsonc)

**Response Fields**: Same as `generar_comprobante` response, plus:
- `anulado`: Boolean - whether document has been voided

**Use Cases**:
- Check SUNAT acceptance status after async generation
- Retrieve PDF/XML/CDR URLs
- Verify void status

---

### 3. generar_anulacion

**Purpose**: Void (annul) a previously generated document.

**Endpoint**: `POST /api/v1/<client-route>`

**Request Example**: See [`json-v1-generar-anulacion-request.json`](../assets/json-v1-generar-anulacion-request.json) and [`json-v1-generar-anulacion-request.jsonc`](../assets/json-v1-generar-anulacion-request.jsonc)

**Request Fields**:
- `operacion`: Always "generar_anulacion"
- `tipo_de_comprobante`: Type of document to void (1-4)
- `serie`: Series of document to void
- `numero`: Number of document to void
- `motivo`: Reason for voiding (required, max 100 characters)
- `codigo_unico`: Optional unique code for idempotency

**Response Example**: See [`json-v1-generar-anulacion-response.json`](../assets/json-v1-generar-anulacion-response.json) and [`json-v1-generar-anulacion-response.jsonc`](../assets/json-v1-generar-anulacion-response.jsonc)

**Response Fields**:
- `numero`: Void request sequence number
- `sunat_ticket_numero`: SUNAT ticket for async processing
- `aceptada_por_sunat`: Boolean (initially `false`, check with `consultar_anulacion`)
- `sunat_description`: Status message (null until processed)
- `sunat_responsecode`: Response code (null until processed)
- `enlace`: NubeFact URL for void request
- `enlace_del_pdf`: URL to download void summary PDF
- `enlace_del_xml`: URL to download void XML
- `enlace_del_cdr`: URL to download void CDR

**Important Notes**:
- Void processing is **asynchronous** via SUNAT
- Initial response will have `aceptada_por_sunat: false`
- Use `consultar_anulacion` to poll for acceptance status
- SUNAT may take time to process void requests

---

### 4. consultar_anulacion

**Purpose**: Check the status of a void request.

**Endpoint**: `POST /api/v1/<client-route>`

**Request Example**: See [`json-v1-consultar-anulacion-request.json`](../assets/json-v1-consultar-anulacion-request.json) and [`json-v1-consultar-anulacion-request.jsonc`](../assets/json-v1-consultar-anulacion-request.jsonc)

**Request Fields**:
- `operacion`: Always "consultar_anulacion"
- `tipo_de_comprobante`: Type of voided document (1-4)
- `serie`: Series of voided document
- `numero`: Number of voided document

**Response Example**: See [`json-v1-consultar-anulacion-response.json`](../assets/json-v1-consultar-anulacion-response.json) and [`json-v1-consultar-anulacion-response.jsonc`](../assets/json-v1-consultar-anulacion-response.jsonc)

**Response Fields**: Same as `generar_anulacion` response

**Polling Strategy**:
- Check `aceptada_por_sunat` field
- If `false`, SUNAT is still processing
- If `true`, check `sunat_responsecode`: "0" = accepted, other = error
- Recommended polling interval: 30-60 seconds

---

## Error Handling

**Error Response Example**: See [`json-v1-error-response.json`](../assets/json-v1-error-response.json) and [`json-v1-error-response.jsonc`](../assets/json-v1-error-response.jsonc)

**Error Structure**:
```json
{
  "errors": "Error message description",
  "codigo": 20
}
```

**Common Error Codes**:
- `20`: Format error - request doesn't comply with required format
- `21`: Validation error - field values don't meet validation rules
- `22`: Business rule error - operation violates business logic
- Other codes: Refer to NubeFact documentation

**SUNAT Error Codes**:
When `aceptada_por_sunat: false` and `sunat_responsecode` is not "0", check `sunat_description` and `sunat_soap_error` for details.

---

## Document Types

### tipo_de_comprobante Values

| Code | Type | Series Prefix | Description |
|------|------|---------------|-------------|
| 1 | Factura | F* | Invoice (for RUC holders) |
| 2 | Boleta | B* | Receipt (for individuals, DNI) |
| 3 | Nota de Crédito | F*/B* | Credit Note (must reference original document) |
| 4 | Nota de Débito | F*/B* | Debit Note (must reference original document) |

### Series Naming Rules

- **Facturas**: 4 characters starting with "F" (e.g., "FFF1", "F001")
- **Boletas**: 4 characters starting with "B" (e.g., "BBB1", "B001")
- **Notes**: Same prefix as the document being modified

---

## Client Document Types

### cliente_tipo_de_documento Values

| Code | Type | Description |
|------|------|-------------|
| 0 | DOC.TRIB.NO.DOM.SIN.RUC | Foreign tax document |
| 1 | DNI | National ID (Documento Nacional de Identidad) |
| 4 | CARNET DE EXTRANJERIA | Foreign resident card |
| 6 | RUC | Tax ID (Registro Único de Contribuyentes) |
| 7 | PASAPORTE | Passport |
| A | CED. DIPLOMATICA DE IDENTIDAD | Diplomatic ID |

---

## Tax Types (IGV)

### tipo_de_igv Values

| Code | Type | Description |
|------|------|-------------|
| 1 | Gravada | Taxable (IGV applies) |
| 2 | Exonerada | Exempt from tax |
| 3 | Inafecta | Unaffected by tax |
| 9 | Gratuita | Free/complimentary |

---

## Amount Fields

All monetary amounts are **numeric** values (integers or decimals with up to 2 decimal places).

### Required Totals Calculation

1. **For each item**:
   - `subtotal` = `valor_unitario` × `cantidad` - `descuento`
   - `igv` = Calculated based on `tipo_de_igv` and `igv_percentage`
   - `total` = `subtotal` + `igv`

2. **Header totals**:
   - `total_gravada` = Sum of all items with `tipo_de_igv` = 1
   - `total_exonerada` = Sum of all items with `tipo_de_igv` = 2
   - `total_inafecta` = Sum of all items with `tipo_de_igv` = 3
   - `total_gratuita` = Sum of all items with `tipo_de_igv` = 9
   - `total_igv` = Sum of all `igv` from items
   - `total_descuento` = Sum of all item discounts + `descuento_global`
   - `total` = `total_gravada` + `total_exonerada` + `total_inafecta` + `total_igv` + `total_otros_cargos` - `total_descuento`

3. **With perception**:
   - `total_incluido_percepcion` = `total` + `total_percepcion`

---

## Units of Measure

### unidad_de_medida Common Values

| Code | Description |
|------|-------------|
| NIU | Unit (general unit) |
| ZZ | Service |
| KGM | Kilogram |
| LTR | Liter |
| MTR | Meter |
| UND | Unit |
| DZN | Dozen |
| BOX | Box |
| SET | Set |

Refer to SUNAT Catalog 03 for complete list.

---

## Best Practices

### 1. Date Format
- Always use DD-MM-YYYY format (e.g., "25-02-2026")
- NEVER use YYYY-MM-DD in API requests
- Issue date cannot be in the future

### 2. Series and Number Management
- Maintain sequential numbering per series
- Don't skip numbers in sequence
- Each series must have its own sequence counter

### 3. Async Processing
- Set `enviar_automaticamente_a_la_sunat: true` for immediate SUNAT submission
- If `false`, you must manually submit later
- Always check `aceptada_por_sunat` before considering document complete

### 4. Void Workflow
1. Call `generar_anulacion` with document details
2. Store `sunat_ticket_numero` from response
3. Poll `consultar_anulacion` every 30-60 seconds
4. Check `aceptada_por_sunat` until `true`
5. Verify `sunat_responsecode` = "0" for success

### 5. Error Recovery
- Log all API requests and responses
- Store `enlace_del_pdf`, `enlace_del_xml`, `enlace_del_cdr` for audit
- Implement retry logic with exponential backoff for network errors
- Never retry 4xx errors without fixing the request

### 6. Testing
- Use test credentials provided by NubeFact
- Test all document types before production
- Verify SUNAT acceptance in test environment

---

## Integration Checklist

- [ ] Store API credentials securely (route + token)
- [ ] Implement request logging for audit trail
- [ ] Handle async void processing with polling
- [ ] Validate amounts calculation matches SUNAT rules
- [ ] Store SUNAT response artifacts (PDF, XML, CDR URLs)
- [ ] Implement error handling for all API calls
- [ ] Test credit/debit note document references
- [ ] Verify series naming conventions
- [ ] Implement date format conversion (DD-MM-YYYY)
- [ ] Test installment payment schedules for credit sales

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
