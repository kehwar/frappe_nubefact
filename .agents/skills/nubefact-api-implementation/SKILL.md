---
name: nubefact-api-implementation
description: Minimal starter skill for implementing and extending NubeFact API integrations in the nubefact app. Use when adding API clients, request payload builders, authentication headers, or response handling.
---

# NubeFact API Implementation

## Minimal workflow

1. Identify the API requirement and expected payload/response.
2. Implement endpoint logic in a focused module.
3. Handle API errors with clear, actionable messages.
4. Add/update tests for the implemented behavior.

## Notes

- Keep changes small and isolated.
- Prefer explicit request and response schemas.
- English is the primary language across this skill (instructions, workflow notes, and general implementation guidance).
- To reduce implementation friction and avoid an unnecessary complex mapping step, DocType names and API-facing field names are intentionally defined in Spanish, following NubeFact API requirements.
- Expand this skill with references/scripts as the integration grows.

## References

- `references/canonical-model.md` — Canonical model index and shared implementation notes.
- `references/cpe-examples.md` — CPE examples index grouped by document/operation.
- `references/gre-examples.md` — GRE examples index grouped by document/operation.
- `references/doctype-nubefact-branch.md` — `Nubefact Branch` DocType specification.
- `references/doctype-nubefact-api-log.md` — `Nubefact API Log` DocType specification.
- `references/doctype-nubefact-guia-remision-schema.md` — `Nubefact Guía de Remisión` (main) DocType schema/specification.
- `references/doctype-nubefact-guia-remision-item-schema.md` — `Nubefact Guía de Remisión Ítem` child DocType schema/specification.
- `references/doctype-nubefact-guia-remision-documento-relacionado-schema.md` — `Nubefact Guía de Remisión Documento Relacionado` child DocType schema/specification.
- `references/doctype-nubefact-guia-remision-vehiculo-secundario-schema.md` — `Nubefact Guía de Remisión Vehículo Secundario` child DocType schema/specification.
- `references/doctype-nubefact-guia-remision-conductor-secundario-schema.md` — `Nubefact Guía de Remisión Conductor Secundario` child DocType schema/specification.
- `references/doctype-nubefact-factura-schema.md` — `Nubefact Factura` DocType schema/specification.
- `references/doctype-nubefact-invoice-guide.md` — `Nubefact Invoice` workflow guide (how to fill fields correctly by scenario).

### CPE API Structure Tables (from `assets/cpe-manual-google-doc.md`)

- `references/cpe-api-estructura-cabecera.md` — ESTRUCTURA PARA GENERAR FACTURAS, BOLETAS Y NOTAS — CABECERA DEL DOCUMENTO.
- `references/cpe-api-estructura-items.md` — PARA ITEMS O LÍNEAS DEL DOCUMENTO.
- `references/cpe-api-estructura-guias.md` — PARA GUÍAS.
- `references/cpe-api-estructura-venta-credito.md` — PARA VENTA AL CRÉDITO.
- `references/cpe-api-estructura-consulta.md` — ESTRUCTURA PARA CONSULTAR FACTURAS, BOLETAS Y NOTAS.
- `references/cpe-api-estructura-respuesta.md` — ESTRUCTURA DE RESPUESTA DE NUBEFACT PARA FACTURAS, BOLETAS, NOTAS.
- `references/cpe-api-estructura-anulacion-generar.md` — ESTRUCTURA PARA GENERAR ANULACIÓN O COMUNICACIÓN DE BAJA.
- `references/cpe-api-estructura-anulacion-consultar.md` — ESTRUCTURA PARA CONSULTAR ANULACIÓN O COMUNICACIÓN DE BAJA.
- `references/cpe-api-estructura-anulacion-respuesta.md` — ESTRUCTURA DE LA RESPUESTA DE NUBEFACT PARA ANULACIÓN O COMUNICACIÓN DE BAJA.

### GRE API Structure Tables (from `assets/gre-manual-google-doc.md`)

- `references/gre-api-estructura-cabecera.md` — ESTRUCTURA PARA GENERAR GUÍA DE REMISIÓN REMITENTE — CABECERA DEL DOCUMENTO.
- `references/gre-api-estructura-items.md` — PARA ITEMS O LÍNEAS DEL DOCUMENTO.
- `references/gre-api-estructura-documentos-relacionados.md` — PARA DOCUMENTOS RELACIONADOS AL DOCUMENTO.
- `references/gre-api-estructura-vehiculos-secundarios.md` — PARA VEHÍCULOS SECUNDARIOS (opcional, máx. 2).
- `references/gre-api-estructura-conductores-secundarios.md` — PARA CONDUCTORES SECUNDARIOS (opcional, máx. 2).
- `references/gre-api-estructura-consulta.md` — ESTRUCTURA PARA CONSULTAR GRE REMITENTE O TRANSPORTISTA.
- `references/gre-api-estructura-respuesta.md` — ESTRUCTURA DE RESPUESTA DE NUBEFACT.

## Example assets

All example files in `assets/` folder:
- `cpe-example-*.json` — CPE request/response examples (see `references/cpe-examples.md`)
- `gre-example-*.json` — GRE request/response examples (see `references/gre-examples.md`)
- `gre-example-xml.xml` — sample SUNAT XML generated for GRE
- `gre-example-cdr.xml` — sample SUNAT CDR (Constancia de Recepción) XML response
- `cpe-manual-google-doc.{md,pdf}` — JSON API v1 source material
- `gre-manual-google-doc.{md,pdf}` — Guía de Remisión API source material

## Source material links

- API (JSON v1): https://docs.google.com/document/d/1QWWSILBbjd4MDkJl7vCkL2RZvkPh0IC7Wa67BvoYIhA
- Guia de Remision API: https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II
- Ejemplos JSON: https://www.nubefact.com/downloads/EJEMPLOS-DE-ARCHIVOS-JSON
