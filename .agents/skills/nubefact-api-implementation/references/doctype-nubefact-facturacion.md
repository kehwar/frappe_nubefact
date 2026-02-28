# DocType: Nubefact Facturacion

**DocType Name**: `Nubefact Facturacion`
**Type**: Standard DocType (non-child)
**Purpose**: Comprobante electrónico de pago — factura, boleta, nota de crédito, nota de débito.

## API-spec Fields

All field names match the NubeFact CPE API spec exactly.

### Sección 1 — Identificación del comprobante (`cpe-api-estructura-cabecera.md`)

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `operacion` | Data | Read-only; default `"generar_comprobante"` |
| `tipo_de_comprobante` | Select | 1=Factura, 2=Boleta, 3=NC, 4=ND |
| `serie` | Data | |
| `numero` | Int | `no_copy`; assigned by NubeFact response |
| `sunat_transaction` | Select | 1–35 |

### Sección 2 — Datos del cliente

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `cliente_tipo_de_documento` | Select | 6, 1, -, 4, 7, A, B, 0, G |
| `cliente_numero_de_documento` | Data | |
| `cliente_denominacion` | Data | |
| `cliente_direccion` | Small Text | |
| `cliente_email` | Data | |
| `cliente_email_1` | Data | |
| `cliente_email_2` | Data | |

### Sección 3 — Fechas y moneda

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `fecha_de_emision` | Date | |
| `fecha_de_vencimiento` | Date | |
| `moneda` | Select | 1=Soles, 2=USD, 3=EUR, 4=GBP |
| `tipo_de_cambio` | Float | |

### Sección 4 — Totales e impuestos globales

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `porcentaje_de_igv` | Float | Default 18 |
| `descuento_global` | Currency | |
| `total_descuento` | Currency | |
| `total_anticipo` | Currency | |
| `total_gravada` | Currency | |
| `total_inafecta` | Currency | |
| `total_exonerada` | Currency | |
| `total_igv` | Currency | |
| `total_gratuita` | Currency | |
| `total_otros_cargos` | Currency | |
| `total_isc` | Currency | |
| `total_impuestos_bolsas` | Currency | |
| `total` | Currency | |

### Sección 5 — Percepción y retención

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `percepcion_tipo` | Data | |
| `percepcion_base_imponible` | Currency | |
| `total_percepcion` | Currency | |
| `total_incluido_percepcion` | Currency | |
| `retencion_tipo` | Data | |
| `retencion_base_imponible` | Currency | |
| `total_retencion` | Currency | |

### Sección 6 — Notas (documento relacionado)

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `documento_que_se_modifica_tipo` | Select | 1, 2 |
| `documento_que_se_modifica_serie` | Data | |
| `documento_que_se_modifica_numero` | Int | |
| `tipo_de_nota_de_credito` | Select | 1–13 |
| `tipo_de_nota_de_debito` | Select | 1–5 |

### Sección 8–10 — Detracción

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `detraccion` | Check | |
| `detraccion_tipo` | Select | |
| `detraccion_total` | Currency | |
| `detraccion_porcentaje` | Float | |
| `medio_de_pago_detraccion` | Select | |
| `ubigeo_origen` | Data | |
| `direccion_origen` | Data | |
| `ubigeo_destino` | Data | |
| `direccion_destino` | Data | |
| `detalle_viaje` | Data | |
| `val_ref_serv_trans` | Currency | |
| `val_ref_carga_efec` | Currency | |
| `val_ref_carga_util` | Currency | |
| `punto_origen_viaje` | Data | |
| `punto_destino_viaje` | Data | |
| `descripcion_tramo` | Data | |
| `val_ref_carga_efec_tramo_virtual` | Currency | |
| `configuracion_vehicular` | Data | |
| `carga_util_tonel_metricas` | Float | |
| `carga_efec_tonel_metricas` | Float | |
| `val_ref_tonel_metrica` | Float | |
| `val_pre_ref_carga_util_nominal` | Currency | |
| `indicador_aplicacion_retorno_vacio` | Check | |
| `matricula_emb_pesquera` | Data | |
| `nombre_emb_pesquera` | Data | |
| `descripcion_tipo_especie_vendida` | Data | |
| `lugar_de_descarga` | Data | |
| `cantidad_especie_vendida` | Float | |
| `fecha_de_descarga` | Date | |

### Sección 11 — Otras características del comprobante

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `enviar_automaticamente_a_la_sunat` | Check | Default 1 |
| `enviar_automaticamente_al_cliente` | Check | Default 0 |
| `codigo_unico` | Data | Falls back to `name` if empty |
| `formato_de_pdf` | Select | A4, A5, TICKET |
| `condiciones_de_pago` | Small Text | |
| `generado_por_contingencia` | Check | |
| `bienes_region_selva` | Check | |
| `servicios_region_selva` | Check | |
| `nubecont_tipo_de_venta_codigo` | Data | |
| `medio_de_pago` | Data | |
| `orden_compra_servicio` | Data | |
| `placa_vehiculo` | Data | |
| `observaciones` | Text | |

### Sección 12 — Estructuras anidadas (child tables)

| Field Name | Frappe Type | Child DocType |
|-----------|------------|---------------|
| `items` | Table | Nubefact Facturacion Item |
| `guias` | Table | Nubefact Facturacion Guia Relacionada |
| `venta_al_credito` | Table | Nubefact Facturacion Cuota |

### Respuesta de NubeFact (`cpe-api-estructura-respuesta.md`)

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `enlace` | Data (URL) | `read_only`, `no_copy` |
| `aceptada_por_sunat` | Check | `read_only`, `no_copy` |
| `sunat_description` | Text | `read_only`, `no_copy` |
| `sunat_note` | Text | `read_only`, `no_copy` |
| `sunat_responsecode` | Data | `read_only`, `no_copy` |
| `sunat_soap_error` | Text | `read_only`, `no_copy` |
| `pdf_zip_base64` | Long Text | `read_only`, `no_copy` |
| `xml_zip_base64` | Long Text | `read_only`, `no_copy` |
| `cdr_zip_base64` | Long Text | `read_only`, `no_copy` |
| `cadena_para_codigo_qr` | Text | `read_only`, `no_copy` |
| `codigo_hash` | Data | `read_only`, `no_copy` |
| `codigo_de_barras` | Text | `read_only`, `no_copy` |
| `enlace_del_pdf` | Data (URL) | `read_only`, `no_copy` |
| `enlace_del_xml` | Data (URL) | `read_only`, `no_copy` |
| `enlace_del_cdr` | Data (URL) | `read_only`, `no_copy` |

### Anulación — campos de solicitud (`cpe-api-estructura-anulacion-generar.md`)

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `motivo` | Small Text | Reason entered by user before voiding |

### Anulación — campos de respuesta (`cpe-api-estructura-anulacion-respuesta.md`)

| Field Name | Frappe Type | Notes |
|-----------|------------|-------|
| `sunat_ticket_numero` | Data | `read_only` |

---

## Extra Fields (not described in NubeFact API source files)

These fields are added to support the Frappe/ERP integration layer and are not sent to the NubeFact API.

| Field Name | Frappe Type | Purpose |
|-----------|------------|---------|
| `title` | Data | Auto-composed display name (`{serie}-{numero}`); `read_only` |
| `status` | Select | Document lifecycle state: `Borrador`, `Pendiente de Aceptación`, `Aceptada`, `Anulada`, `Error`; `read_only`, `no_copy` |
| `local` | Link → Nubefact Local | Selects which NubeFact credentials/route to use for API calls |
| `custom` | JSON | Raw JSON object merged into the outgoing API payload (overrides any computed field); allows one-off customizations without schema changes |
| `skip_field_validation` | Check | Bypasses the required-field validation on save (useful for drafts or imports) |
| `last_sunat_check` | Datetime | Timestamp of the last SUNAT status query; `read_only`, `no_copy` |
| `error_message` | Text | Stores the last system-level error (not from SUNAT); `read_only`, `no_copy` |
| `anulado` | Check | Set to 1 once the void is confirmed by SUNAT; `read_only` |
| `fecha_de_anulacion` | Date | Date when the void was processed; `read_only` |
| `estado_de_anulacion` | Select | `Pendiente`, `Aceptada`, `Rechazada`; tracks the void request lifecycle; `read_only` |

---

## Implementation Status
- ✅ Implemented
- Submit flow: `send_to_nubefact` → `generar_comprobante`
- Query flow: `refresh_sunat_status` → `consultar_comprobante`; scheduled via `poll_pending_invoices`
- Void flow: `void_in_nubefact` → `generar_anulacion`
