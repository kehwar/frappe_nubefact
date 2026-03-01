# DocType: Nubefact Guia De Remision

**DocType Name**: `Nubefact Guia De Remision`
**Type**: Standard DocType (submittable-style via `status` field)
**Purpose**: Guía de Remisión Electrónica (GRE) — Remitente (tipo 7) y Transportista (tipo 8).

**API References**:
- Cabecera: `gre-api-estructura-cabecera.md`
- Ítems: `gre-api-estructura-items.md`
- Documentos relacionados: `gre-api-estructura-documentos-relacionados.md`
- Vehículos secundarios: `gre-api-estructura-vehiculos-secundarios.md`
- Conductores secundarios: `gre-api-estructura-conductores-secundarios.md`
- Consulta: `gre-api-estructura-consulta.md`
- Respuesta: `gre-api-estructura-respuesta.md`

---

## Extra Fields (not described in NubeFact API source files)

These fields are added to support the Frappe/ERP integration layer and are **not sent to the NubeFact API**.

| Field Name | Frappe Type | Purpose |
|-----------|------------|---------|
| `title` | Data | Auto-composed display name (`{serie}-{numero:06}`); `read_only` |
| `status` | Select | Document lifecycle: `Borrador` / `Pendiente de Aceptacion` / `Aceptada` / `Error`; `read_only`, `no_copy` |
| `local` | Link → Nubefact Local | Selects which NubeFact credentials/route to use; auto-filled from last used local for the user |
| `custom` | JSON | Raw JSON merged into outgoing API payload at send time (overrides any computed field); per-row `custom` also available in all child tables |
| `skip_field_validation` | Check | Bypasses required-field checks on save (useful for drafts or imports) |
| `last_sunat_check` | Datetime | Timestamp of last SUNAT status query; `read_only`, `no_copy` |
| `error_message` | Text | Last system-level or SUNAT error captured during send or refresh; `read_only`, `no_copy` |

---

## API-spec Fields — Cabecera (Request)

All fields map directly to the NubeFact GRE API (`operacion: "generar_guia"`).

> `operacion` is always `"generar_guia"` — hardcoded in the payload builder, not stored in the DocType.

### Identificación del Documento

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `tipo_de_comprobante` | Select | `tipo_de_comprobante` | Obl. | `7` = GRE Remitente, `8` = GRE Transportista |
| `serie` | Data | `serie` | Obl. | Empieza con `T` para tipo 7, `V` para tipo 8 |
| `numero` | Int | `numero` | Obl. | Correlativo; asignado desde respuesta API; `no_copy` |
| `fecha_de_emision` | Date | `fecha_de_emision` | Obl. | Almacenado como `YYYY-MM-DD`; enviado como `DD-MM-YYYY` |
| `fecha_de_inicio_de_traslado` | Date | `fecha_de_inicio_de_traslado` | Obl. | Almacenado como `YYYY-MM-DD`; enviado como `DD-MM-YYYY` |

### Datos del Cliente / Destinatario

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `cliente_tipo_de_documento` | Select | `cliente_tipo_de_documento` | Obl. | `6`=RUC, `1`=DNI, `4`=CE, `7`=Pasaporte, `A`=Cédula Diplomática, `0`=No domiciliado. Para tipo 7 = Destinatario; para tipo 8 = Remitente. |
| `cliente_numero_de_documento` | Data | `cliente_numero_de_documento` | Obl. | |
| `cliente_denominacion` | Data | `cliente_denominacion` | Obl. | |
| `cliente_direccion` | Small Text | `cliente_direccion` | Obl. | |
| `cliente_email` | Data | `cliente_email` | Opc. | |
| `cliente_email_1` | Data | `cliente_email_1` | Opc. | |
| `cliente_email_2` | Data | `cliente_email_2` | Opc. | |

### Destinatario (solo GRE Transportista, tipo 8)

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `destinatario_documento_tipo` | Select | `destinatario_documento_tipo` | Cond. | Solo para tipo 8 |
| `destinatario_documento_numero` | Data | `destinatario_documento_numero` | Cond. | Solo para tipo 8 |
| `destinatario_denominacion` | Data | `destinatario_denominacion` | Cond. | Solo para tipo 8 |

### Datos del Traslado

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `motivo_de_traslado` | Select | `motivo_de_traslado` | Obl. (tipo 7) | `01`–`19`; solo GRE Remitente |
| `motivo_de_traslado_otros_descripcion` | Data | `motivo_de_traslado_otros_descripcion` | Opc. | Solo si motivo = `13` |
| `documento_relacionado_codigo` | Select | `documento_relacionado_codigo` | Cond. | `50` o `52`; solo para importación/exportación |
| `tipo_de_transporte` | Select | `tipo_de_transporte` | Obl. (tipo 7) | `01`=Público, `02`=Privado; solo GRE Remitente |
| `peso_bruto_total` | Float | `peso_bruto_total` | Obl. | En kilogramos |
| `peso_bruto_unidad_de_medida` | Select | `peso_bruto_unidad_de_medida` | Obl. | `KGM` o `TNE` |
| `numero_de_bultos` | Int | `numero_de_bultos` | Obl. (tipo 7) | Solo GRE Remitente |
| `observaciones` | Text | `observaciones` | Opc. | Hasta 1000 caracteres |

### Transportista (solo tipo 7, transporte público)

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `transportista_documento_tipo` | Select | `transportista_documento_tipo` | Cond. | Solo cuando `tipo_de_transporte = 01` |
| `transportista_documento_numero` | Data | `transportista_documento_numero` | Cond. | Solo cuando `tipo_de_transporte = 01` |
| `transportista_denominacion` | Data | `transportista_denominacion` | Cond. | Solo cuando `tipo_de_transporte = 01` |
| `transportista_placa_numero` | Data | `transportista_placa_numero` | Obl. | GRE Remitente y Transportista |
| `tuc_vehiculo_principal` | Data | `tuc_vehiculo_principal` | Opc. | Solo GRE Transportista; TUC o Certificado de Habilitación vehicular; mayúsculas y números, sin guiones |

### Conductor Principal

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `conductor_documento_tipo` | Select | `conductor_documento_tipo` | Cond. | Tipo 7: solo cuando `tipo_de_transporte = 02`. Tipo 8: obligatorio. |
| `conductor_documento_numero` | Data | `conductor_documento_numero` | Cond. | Ídem |
| `conductor_denominacion` | Data | `conductor_denominacion` | Cond. | Nombre completo del conductor. Tipo 7: solo cuando `tipo_de_transporte = 02`. Tipo 8: obligatorio. |
| `conductor_nombre` | Data | `conductor_nombre` | Cond. | Ídem |
| `conductor_apellidos` | Data | `conductor_apellidos` | Cond. | Ídem |
| `conductor_numero_licencia` | Data | `conductor_numero_licencia` | Cond. | Ídem |
| `mtc` | Data | `mtc` | Opc. | Autorización MTC; solo mayúsculas y números alfanuméricos |
| `sunat_envio_indicador` | Select | `sunat_envio_indicador` | Opc. | `01`–`06`; ver spec cabecera |

### Subcontratador (condicional: `sunat_envio_indicador = 02`)

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `subcontratador_documento_tipo` | Select | `subcontratador_documento_tipo` | Cond. | Solo `6` = RUC |
| `subcontratador_documento_numero` | Data | `subcontratador_documento_numero` | Cond. | 11 caracteres exactos |
| `subcontratador_denominacion` | Data | `subcontratador_denominacion` | Cond. | |

### Pagador del Servicio (condicional: `sunat_envio_indicador = 03`)

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `pagador_servicio_documento_tipo_identidad` | Select | `pagador_servicio_documento_tipo_identidad` | Cond. | `6`, `1`, `4`, `7`, `A`, `0` |
| `pagador_servicio_documento_numero_identidad` | Data | `pagador_servicio_documento_numero_identidad` | Cond. | Hasta 15 caracteres |
| `pagador_servicio_denominacion` | Data | `pagador_servicio_denominacion` | Cond. | |

### Punto de Partida / Llegada

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `punto_de_partida_ubigeo` | Data | `punto_de_partida_ubigeo` | Obl. | Código ubigeo SUNAT; auto-completado desde `local` |
| `punto_de_partida_direccion` | Small Text | `punto_de_partida_direccion` | Obl. | Auto-completado desde `local` |
| `punto_de_partida_codigo_establecimiento_sunat` | Data | `punto_de_partida_codigo_establecimiento_sunat` | Cond. | Para motivos `04`, `18` |
| `punto_de_llegada_ubigeo` | Data | `punto_de_llegada_ubigeo` | Obl. | |
| `punto_de_llegada_direccion` | Small Text | `punto_de_llegada_direccion` | Obl. | |
| `punto_de_llegada_codigo_establecimiento_sunat` | Data | `punto_de_llegada_codigo_establecimiento_sunat` | Cond. | Para motivos `04`, `18` |

### Otras Configuraciones

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `enviar_automaticamente_al_cliente` | Check | `enviar_automaticamente_al_cliente` | Opc. | Enviado como `"true"` / `"false"` |
| `formato_de_pdf` | Select | `formato_de_pdf` | Opc. | `A4`, `A5`, `TICKET`; vacío = por defecto de NUBEFACT |

---

## API-spec Fields — Estructuras Anidadas (child tables)

### Ítems (`gre-api-estructura-items.md`) — child: `Nubefact Guia De Remision Item`

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `unidad_de_medida` | Data | `unidad_de_medida` | Obl. | `NIU`, `ZZ` u otros |
| `codigo` | Data | `codigo` | Opc. | |
| `descripcion` | Data | `descripcion` | Obl. | |
| `cantidad` | Float | `cantidad` | Obl. | Enviado como string |
| `codigo_dam` | Data | `codigo_dam` | Cond. | Solo para importación/exportación |
| `custom` | JSON | — | — | Datos crudos mezclados en el payload de la fila |

### Documentos Relacionados (`gre-api-estructura-documentos-relacionados.md`) — child: `Nubefact Guia De Remision Documento Relacionado`

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `tipo` | Select | `tipo` | Obl. | `01`=Factura, `03`=Boleta, `09`=GRE Remitente, `31`=GRE Transportista |
| `serie` | Data | `serie` | Obl. | |
| `numero` | Int | `numero` | Obl. | |
| `custom` | JSON | — | — | Datos crudos mezclados en el payload de la fila |

### Vehículos Secundarios (`gre-api-estructura-vehiculos-secundarios.md`) — child: `Nubefact Guia De Remision Vehiculo Secundario`

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `placa_numero` | Data | `placa_numero` | Obl. | Hasta 2 vehículos |
| `tuc` | Data | `tuc` | Opc. | Solo GRE Transportista |
| `custom` | JSON | — | — | Datos crudos mezclados en el payload de la fila |

### Conductores Secundarios (`gre-api-estructura-conductores-secundarios.md`) — child: `Nubefact Guia De Remision Conductor Secundario`

| Field Name | Frappe Type | API Field | Req. | Notes |
|-----------|------------|-----------|------|-------|
| `documento_tipo` | Select | `documento_tipo` | Cond. | Tipo 7: solo cuando `tipo_de_transporte = 02` |
| `documento_numero` | Data | `documento_numero` | Cond. | |
| `nombre` | Data | `nombre` | Cond. | |
| `apellidos` | Data | `apellidos` | Cond. | |
| `numero_licencia` | Data | `numero_licencia` | Cond. | Hasta 2 conductores |
| `custom` | JSON | — | — | Datos crudos mezclados en el payload de la fila |

---

## API-spec Fields — Respuesta (`gre-api-estructura-respuesta.md`)

| Field Name | Frappe Type | API Field | Notes |
|-----------|------------|-----------|-------|
| `aceptada_por_sunat` | Check | `aceptada_por_sunat` | `read_only`, `no_copy` |
| `sunat_responsecode` | Data | `sunat_responsecode` | `read_only`, `no_copy` |
| `sunat_description` | Text | `sunat_description` | `read_only`, `no_copy` |
| `sunat_note` | Text | `sunat_note` | `read_only`, `no_copy` |
| `sunat_soap_error` | Text | `sunat_soap_error` | `read_only`, `no_copy` |
| `enlace` | Data (URL) | `enlace` | `read_only`, `no_copy` |
| `enlace_del_pdf` | Data (URL) | `enlace_del_pdf` | `read_only`, `no_copy` |
| `enlace_del_xml` | Data (URL) | `enlace_del_xml` | `read_only`, `no_copy` |
| `enlace_del_cdr` | Data (URL) | `enlace_del_cdr` | `read_only`, `no_copy` |
| `cadena_para_codigo_qr` | Data | `cadena_para_codigo_qr` | `read_only`, `no_copy` |

> `pdf_zip_base64`, `xml_zip_base64`, `cdr_zip_base64` are returned by the API when enabled in NUBEFACT settings, but are **not stored** in this DocType.

---

## Implementation Status

- ✅ Implemented
- Submit flow: `enviar_a_nubefact` → `generar_guia`
- Query flow: `refrescar_estado_sunat` → `consultar_guia`; scheduled via `consultar_guias_pendientes`
