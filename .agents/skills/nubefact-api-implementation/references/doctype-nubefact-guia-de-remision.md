# DocType: Nubefact Guia De Remision

**DocType Name**: `Nubefact Guia De Remision`
**Type**: Standard DocType (submittable-style via `status` field)
**Purpose**: Stores and manages Guías de Remisión Electrónica (GRE) — both Remitente (type 7) and Transportista (type 8).

**API References**:
- Cabecera: `gre-api-estructura-cabecera.md`
- Ítems: `gre-api-estructura-items.md`
- Documentos relacionados: `gre-api-estructura-documentos-relacionados.md`
- Vehículos secundarios: `gre-api-estructura-vehiculos-secundarios.md`
- Conductores secundarios: `gre-api-estructura-conductores-secundarios.md`
- Consulta: `gre-api-estructura-consulta.md`
- Respuesta: `gre-api-estructura-respuesta.md`

---

## Frappe-spec Fields (non-API)

These fields are added by this implementation and are **not part of the NubeFact API payload**.

| Field Label | Field Name | Field Type | Notes |
|-------------|------------|------------|-------|
| Título | `title` | Data (read-only) | Auto-generated as `SERIE-NNNNNN`. Used as the Frappe document display name. |
| Estado | `status` | Select (read-only) | `Borrador` / `Pendiente de Aceptacion` / `Aceptada` / `Error`. Drives document lifecycle. |
| Local | `local` | Link → Nubefact Local | Credentials and origin values (ubigeo, dirección). Auto-filled from last used local for the user. |
| Omitir Validación de Campos Obligatorios | `skip_field_validation` | Check | Bypasses required-field checks for edge cases. |
| Datos Crudos | `custom` | JSON | Raw JSON merged into the API payload at send time, overriding any field. Applied per row in child tables too. |
| Última Consulta SUNAT | `last_sunat_check` | Datetime (read-only) | Timestamp of the most recent SUNAT status check. |
| Mensaje de Error | `error_message` | Text (read-only) | Internal error captured during send or refresh. |

---

## API-spec Fields — Cabecera (Request)

All fields map directly to the NubeFact GRE API (`operacion: "generar_guia"`).

> `operacion` is always `"generar_guia"` — hardcoded in the payload builder, not stored in the DocType.

### Identificación del Documento

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Tipo de Comprobante | `tipo_de_comprobante` | Select | `tipo_de_comprobante` | Obl. | `7` = GRE Remitente, `8` = GRE Transportista |
| Serie | `serie` | Data | `serie` | Obl. | Starts with `T` for type 7, `V` for type 8 |
| Número | `numero` | Int | `numero` | Obl. | Correlative; auto-set from API response |
| Fecha de Emisión | `fecha_de_emision` | Date | `fecha_de_emision` | Obl. | Stored as `YYYY-MM-DD`; sent as `DD-MM-YYYY` |
| Fecha de Inicio de Traslado | `fecha_de_inicio_de_traslado` | Date | `fecha_de_inicio_de_traslado` | Obl. | Stored as `YYYY-MM-DD`; sent as `DD-MM-YYYY` |

### Datos del Cliente / Destinatario

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Cliente Tipo de Documento | `cliente_tipo_de_documento` | Select | `cliente_tipo_de_documento` | Obl. | `6`=RUC, `1`=DNI, `4`=CE, `7`=Pasaporte, `A`=Cédula Diplomática, `0`=No domiciliado. For type 7 = Destinatario; for type 8 = Remitente. |
| Cliente Número de Documento | `cliente_numero_de_documento` | Data | `cliente_numero_de_documento` | Obl. | |
| Cliente Denominación | `cliente_denominacion` | Data | `cliente_denominacion` | Obl. | |
| Cliente Dirección | `cliente_direccion` | Small Text | `cliente_direccion` | Obl. | |
| Cliente Email | `cliente_email` | Data | `cliente_email` | Opc. | |
| Cliente Email 1 | `cliente_email_1` | Data | `cliente_email_1` | Opc. | |
| Cliente Email 2 | `cliente_email_2` | Data | `cliente_email_2` | Opc. | |
| Destinatario Documento Tipo | `destinatario_documento_tipo` | Select | `destinatario_documento_tipo` | Cond. | Only for GRE Transportista (type 8). Same options as `cliente_tipo_de_documento`. |
| Destinatario Documento Número | `destinatario_documento_numero` | Data | `destinatario_documento_numero` | Cond. | Only for GRE Transportista (type 8). |
| Destinatario Denominación | `destinatario_denominacion` | Data | `destinatario_denominacion` | Cond. | Only for GRE Transportista (type 8). |

### Datos del Traslado

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Motivo de Traslado | `motivo_de_traslado` | Select | `motivo_de_traslado` | Obl. (tipo 7) | `01`=Venta, `02`=Compra, `04`=Traslado misma empresa, `05`=Consignación, `06`=Devolución, `07`=Recojo bienes, `08`=Importación, `09`=Exportación, `13`=Otros, `14`=Venta sujeta a confirmación, `17`=Transformación, `18`=Itinerante, `19`=Otros |
| Motivo de Traslado Otros Descripción | `motivo_de_traslado_otros_descripcion` | Data | `motivo_de_traslado_otros_descripcion` | Cond. | Required when `motivo_de_traslado` = `13`. |
| Documento Relacionado Código | `documento_relacionado_codigo` | Select | `documento_relacionado_codigo` | Cond. | `50`=DAM, `52`=DS. Only for import/export motivos. |
| Tipo de Transporte | `tipo_de_transporte` | Select | `tipo_de_transporte` | Obl. (tipo 7) | `01`=Público, `02`=Privado. |
| Peso Bruto Total | `peso_bruto_total` | Float | `peso_bruto_total` | Obl. | In kilograms (KGM) or tons (TNE). Must be > 0. |
| Peso Bruto Unidad de Medida | `peso_bruto_unidad_de_medida` | Select | `peso_bruto_unidad_de_medida` | Obl. | `KGM` = Kilogramos, `TNE` = Toneladas. |
| Número de Bultos | `numero_de_bultos` | Int | `numero_de_bultos` | Obl. (tipo 7) | Integer, only for GRE Remitente. |
| Transportista Documento Tipo | `transportista_documento_tipo` | Select | `transportista_documento_tipo` | Cond. | Required when `tipo_de_transporte` = `01` (public). Only `6`=RUC accepted. |
| Transportista Documento Número | `transportista_documento_numero` | Data | `transportista_documento_numero` | Cond. | Required when `tipo_de_transporte` = `01`. |
| Transportista Denominación | `transportista_denominacion` | Data | `transportista_denominacion` | Cond. | Required when `tipo_de_transporte` = `01`. |
| Transportista Placa Número | `transportista_placa_numero` | Data | `transportista_placa_numero` | Obl. | No zeros or dashes. 6–8 characters. |
| TUC Vehículo Principal | `tuc_vehiculo_principal` | Data | `tuc_vehiculo_principal` | Opc. | For GRE Transportista. Tarjeta Única de Circulación. Uppercase alphanumeric, no dashes. 10–15 chars. |

### Conductor Principal

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Conductor Documento Tipo | `conductor_documento_tipo` | Select | `conductor_documento_tipo` | Cond. | `1`=DNI, `4`=CE, `7`=Pasaporte. Required for type 7 private transport and all type 8. |
| Conductor Documento Número | `conductor_documento_numero` | Data | `conductor_documento_numero` | Cond. | 1–15 chars. |
| Conductor Denominación | `conductor_denominacion` | Data | `conductor_denominacion` | Cond. | Full conductor name (combined form). |
| Conductor Nombre | `conductor_nombre` | Data | `conductor_nombre` | Cond. | First name. Required for private transport. |
| Conductor Apellidos | `conductor_apellidos` | Data | `conductor_apellidos` | Cond. | Last name(s). Required for private transport. |
| Conductor Número Licencia | `conductor_numero_licencia` | Data | `conductor_numero_licencia` | Cond. | 9–10 chars. Required for private transport. |

### Puntos de Partida y Llegada

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Punto de Partida Ubigeo | `punto_de_partida_ubigeo` | Data | `punto_de_partida_ubigeo` | Obl. | SUNAT ubigeo code. Auto-filled from `local`. |
| Punto de Partida Dirección | `punto_de_partida_direccion` | Small Text | `punto_de_partida_direccion` | Obl. | Up to 150 chars. Auto-filled from `local`. |
| Punto de Partida Código Establecimiento SUNAT | `punto_de_partida_codigo_establecimiento_sunat` | Data | `punto_de_partida_codigo_establecimiento_sunat` | Cond. | Required for motivos `04` and `18`. 4 chars. Auto-filled from `local`. |
| Punto de Llegada Ubigeo | `punto_de_llegada_ubigeo` | Data | `punto_de_llegada_ubigeo` | Obl. | |
| Punto de Llegada Dirección | `punto_de_llegada_direccion` | Small Text | `punto_de_llegada_direccion` | Obl. | |
| Punto de Llegada Código Establecimiento SUNAT | `punto_de_llegada_codigo_establecimiento_sunat` | Data | `punto_de_llegada_codigo_establecimiento_sunat` | Cond. | Required for motivos `04` and `18`. |

### Información Adicional

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Observaciones | `observaciones` | Text | `observaciones` | Opc. | Use `<br>` for line breaks in printed representation. |
| MTC | `mtc` | Data | `mtc` | Opc. | MTC authorization. Uppercase alphanumeric only. Up to 20 chars. |
| SUNAT Envio Indicador | `sunat_envio_indicador` | Select | `sunat_envio_indicador` | Opc. | `01`=PagadorFlete_Remitente, `02`=PagadorFlete_Subcontratador, `03`=PagadorFlete_Tercero, `04`=RetornoVehiculoEnvaseVacio, `05`=RetornoVehiculoVacio, `06`=TrasladoVehiculoM1L |

### Subcontratista (condicional)

> Required only when `sunat_envio_indicador` = `02`.

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Subcontratador Documento Tipo | `subcontratador_documento_tipo` | Select | `subcontratador_documento_tipo` | Cond. | Only `6`=RUC accepted. |
| Subcontratador Documento Número | `subcontratador_documento_numero` | Data | `subcontratador_documento_numero` | Cond. | 11 chars exactly. |
| Subcontratador Denominación | `subcontratador_denominacion` | Data | `subcontratador_denominacion` | Cond. | Up to 250 chars. |

### Pagador del Servicio (condicional)

> Required only when `sunat_envio_indicador` = `03`.

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Pagador Servicio Tipo de Documento | `pagador_servicio_documento_tipo_identidad` | Select | `pagador_servicio_documento_tipo_identidad` | Cond. | `6`=RUC, `1`=DNI, `4`=CE, `7`=Pasaporte, `A`=Cédula Diplomática, `0`=No domiciliado. |
| Pagador Servicio Número de Documento | `pagador_servicio_documento_numero_identidad` | Data | `pagador_servicio_documento_numero_identidad` | Cond. | Up to 15 chars. |
| Pagador Servicio Denominación | `pagador_servicio_denominacion` | Data | `pagador_servicio_denominacion` | Cond. | Up to 250 chars. |

### Configuración

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Enviar Automáticamente al Cliente | `enviar_automaticamente_al_cliente` | Check | `enviar_automaticamente_al_cliente` | Cond. | Sent as `"true"` or `"false"`. Only triggers if SUNAT accepts the GRE. |
| Formato de PDF | `formato_de_pdf` | Select | `formato_de_pdf` | Opc. | `A4` or `TICKET`. Blank = NubeFact default. |

---

## API-spec Fields — Child Tables

### Ítems (`items`) → DocType: Nubefact Guia De Remision Item

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Unidad de Medida | `unidad_de_medida` | Data | `unidad_de_medida` | Obl. | `NIU`=Producto, `ZZ`=Servicio, or Catálogo 65 codes for import/export. |
| Código | `codigo` | Data | `codigo` | Opc. | Internal product code. |
| Descripción | `descripcion` | Text | `descripcion` | Obl. | 1–250 chars. |
| Cantidad | `cantidad` | Float | `cantidad` | Obl. | Up to 12 integer digits, 10 decimal places. |
| Código DAM | `codigo_dam` | Data | `codigo_dam` | Cond. | Only for import/export motivos. 23 chars. |
| Datos Crudos | `custom` | JSON | — | — | Raw JSON merged into item payload at send time. |

### Documentos Relacionados (`documento_relacionado`) → DocType: Nubefact Guia De Remision Documento Relacionado

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Tipo | `tipo` | Select | `tipo` | Obl. | `01`=Factura, `03`=Boleta, `09`=GRE Remitente, `31`=GRE Transportista. |
| Serie | `serie` | Data | `serie` | Obl. | 4 chars. |
| Número | `numero` | Data | `numero` | Obl. | Correlative, no leading zeros. |
| Datos Crudos | `custom` | JSON | — | — | Raw JSON merged into row payload at send time. |

### Vehículos Secundarios (`vehiculos_secundarios`) → DocType: Nubefact Guia De Remision Vehiculo Secundario

> Optional, maximum 2 vehicles.

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Placa Número | `placa_numero` | Data | `placa_numero` | Obl. | 6–8 chars. No zeros or dashes. |
| TUC | `tuc` | Data | `tuc` | Opc. | For GRE Transportista. 10–15 alphanumeric chars. |
| Datos Crudos | `custom` | JSON | — | — | Raw JSON merged into row payload at send time. |

### Conductores Secundarios (`conductores_secundarios`) → DocType: Nubefact Guia De Remision Conductor Secundario

> Optional, maximum 2 conductors.

| Field Label | Field Name | Field Type | API Field | Req. | Notes |
|-------------|------------|------------|-----------|------|-------|
| Documento Tipo | `documento_tipo` | Select | `documento_tipo` | Cond. | `1`=DNI, `4`=CE, `7`=Pasaporte. Required for private transport. |
| Documento Número | `documento_numero` | Data | `documento_numero` | Cond. | 1–15 chars. |
| Nombre | `nombre` | Data | `nombre` | Cond. | First name. Required for private transport. |
| Apellidos | `apellidos` | Data | `apellidos` | Cond. | Last name(s). Required for private transport. |
| Número de Licencia | `numero_licencia` | Data | `numero_licencia` | Cond. | 9–10 chars. Required for private transport. |
| Datos Crudos | `custom` | JSON | — | — | Raw JSON merged into row payload at send time. |

---

## API-spec Fields — Respuesta SUNAT (Response)

These fields are populated when NubeFact returns a response (on send or status poll).

| Field Label | Field Name | Field Type | API Field | Notes |
|-------------|------------|------------|-----------|-------|
| Aceptada por SUNAT | `aceptada_por_sunat` | Check (read-only) | `aceptada_por_sunat` | `true`/`false` from API → `1`/`0`. |
| SUNAT Responsecode | `sunat_responsecode` | Data (read-only) | `sunat_responsecode` | SUNAT response code. |
| SUNAT Description | `sunat_description` | Text (read-only) | `sunat_description` | SUNAT error or acceptance description. |
| SUNAT Note | `sunat_note` | Text (read-only) | `sunat_note` | Additional SUNAT note. |
| SUNAT SOAP Error | `sunat_soap_error` | Text (read-only) | `sunat_soap_error` | Non-SUNAT errors that prevented submission. |
| Enlace | `enlace` | Data/URL (read-only) | `enlace` | Unique NubeFact link. Append `.pdf` for PDF. Only set when SUNAT accepted. |
| Enlace del PDF | `enlace_del_pdf` | Data/URL (read-only) | `enlace_del_pdf` | Full PDF link. Only set when SUNAT accepted. |
| Enlace del XML | `enlace_del_xml` | Data/URL (read-only) | `enlace_del_xml` | Full XML link. Only set when SUNAT accepted. |
| Enlace del CDR | `enlace_del_cdr` | Data/URL (read-only) | `enlace_del_cdr` | Full CDR link. Only set when SUNAT accepted. |
| Cadena para Código QR | `cadena_para_codigo_qr` | Data (read-only) | `cadena_para_codigo_qr` | Data string for QR code generation. |
| PDF ZIP Base64 | `pdf_zip_base64` | Long Text (read-only) | `pdf_zip_base64` | Zipped PDF in base64. Must be enabled in NubeFact settings. |
| XML ZIP Base64 | `xml_zip_base64` | Long Text (read-only) | `xml_zip_base64` | Zipped XML in base64. Must be enabled in NubeFact settings. |
| CDR ZIP Base64 | `cdr_zip_base64` | Long Text (read-only) | `cdr_zip_base64` | Zipped CDR in base64. Must be enabled in NubeFact settings. |

---

## Implementation Status

- ✅ Implemented
- `enviar_a_nubefact(name)` — Sends the GRE using `operacion: "generar_guia"`.
- `refrescar_estado_sunat(name)` — Polls NubeFact using `operacion: "consultar_guia"`.
- `consultar_guias_pendientes()` — Scheduled job that polls all `Pendiente de Aceptacion` GREs (batch of 20).
- Field validation is governed by `nubefact_guia_de_remision_schema.py`.
- All child table rows support `custom` JSON overrides via `apply_raw_payload_overrides`.
