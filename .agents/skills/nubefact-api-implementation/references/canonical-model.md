# Canonical Model - NubeFact Frappe DocTypes

This index describes the canonical NubeFact Frappe model and links to per-DocType reference files.

---

## Current Implementation Status (as of 2026-02-27)

| Object | Status | Notes |
|--------|--------|-------|
| Nubefact Local | ✅ Implemented | Active credentials container per local/company. Uses `ruta_api` + `token_api`. |
| Nubefact API Log | ✅ Implemented | Request/response logging active. Uses `status` (`Success`/`Error`) and script-based naming from `request_timestamp`. Uses `local` and `reference_invoice` links. |
| Request API Utility (`make_request`) | ✅ Implemented | Sends POST requests, handles errors, and writes API log entries. |
| Nubefact Guia De Remision | ✅ Implemented | Active submit/query flow. `enviar_a_nubefact`, `refrescar_estado_sunat`, and `consultar_guias_pendientes` are fully implemented. All GRE API fields including `tuc_vehiculo_principal`, `conductor_denominacion`, `mtc`, `sunat_envio_indicador`, subcontractor, and service payer fields are present. Response fields stored: `enlace`, `enlace_del_pdf`, `enlace_del_xml`, `enlace_del_cdr`, `cadena_para_codigo_qr`. |
| Nubefact Facturacion | ✅ Implemented | Submit/query/void flow active. `send_to_nubefact`, `refresh_sunat_status`, `void_in_nubefact`, and `poll_pending_invoices` are implemented. Child tables: Item, Guia Relacionada, Cuota. |

---

## DocType References

1. [Nubefact Local](./doctype-nubefact-local.md)
2. [Nubefact Guia De Remision](./doctype-nubefact-guia-de-remision.md)
3. [Nubefact Facturacion](./doctype-nubefact-facturacion.md)

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
