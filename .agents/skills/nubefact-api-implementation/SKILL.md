---
name: nubefact-api-implementation
description: Minimal starter skill for implementing and extending NubeFact API integrations in the nubefact app. Use when adding API clients, request payload builders, authentication headers, or response handling.
---

# NubeFact API Implementation

Minimal skill scaffold for NubeFact API work in this repository.

## Use this skill when

- Implementing new NubeFact API endpoints
- Refactoring API request/response handling
- Adding authentication and header handling
- Creating reusable payload builder utilities

## Minimal workflow

1. Identify the API requirement and expected payload/response.
2. Implement endpoint logic in a focused module.
3. Handle API errors with clear, actionable messages.
4. Add/update tests for the implemented behavior.

## Notes

- Keep changes small and isolated.
- Prefer explicit request and response schemas.
- Expand this skill with references/scripts as the integration grows.

## References

- `references/canonical-model.md` — Canonical model index and shared implementation notes.
- `references/cpe-examples.md` — CPE examples index grouped by document/operation.
- `references/gre-examples.md` — GRE examples index grouped by document/operation.
- `references/doctype-nubefact-branch.md` — `Nubefact Branch` DocType specification.
- `references/doctype-nubefact-api-log.md` — `Nubefact API Log` DocType specification.
- `references/doctype-nubefact-delivery-note.md` — `Nubefact Delivery Note` DocType specification.
- `references/doctype-nubefact-invoice-schema.md` — `Nubefact Invoice` DocType schema/specification.
- `references/doctype-nubefact-invoice-guide.md` — `Nubefact Invoice` workflow guide (how to fill fields correctly by scenario).

## Example assets

All example files in `assets/` folder:
- `cpe-example-*.json` — CPE request/response examples (see `references/cpe-examples.md`)
- `gre-example-*.json` — GRE request/response examples (see `references/gre-examples.md`)
- `gre-example-xml.xml` — sample SUNAT XML generated for GRE
- `gre-example-cdr.xml` — sample SUNAT CDR (Constancia de Recepción) XML response
- `cpe-manual-google-doc.{md,pdf}` — JSON API v1 source material
- `gre-manual-google-doc.{md,pdf}` — Guía de Remisión API source material

## Original docs

- API (JSON v1): https://docs.google.com/document/d/1QWWSILBbjd4MDkJl7vCkL2RZvkPh0IC7Wa67BvoYIhA
- Guia de Remision API: https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II
- Ejemplos JSON: https://www.nubefact.com/downloads/EJEMPLOS-DE-ARCHIVOS-JSON
