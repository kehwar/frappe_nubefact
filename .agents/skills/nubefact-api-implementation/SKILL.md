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
- `references/doctype-nubefact-branch.md` — `Nubefact Branch` DocType specification.
- `references/doctype-nubefact-api-log.md` — `Nubefact API Log` DocType specification.
- `references/doctype-nubefact-delivery-note.md` — `Nubefact Delivery Note` DocType specification.
- `references/doctype-nubefact-invoice.md` — `Nubefact Invoice` DocType specification.
- `references/json-v1-manual.md` — **JSON API v1 Manual** - Complete API documentation transcribed from PDF with operation details, field descriptions, and workflow guides.
- `references/guia-remision-v1-manual.md` — **Guía de Remisión API Manual** - Complete delivery guide API documentation with two-step workflow, Remitente/Transportista flows, and SUNAT acceptance polling.

## Example assets

All example files in `assets/` folder:
- `json-v1-*` — request/response examples from JSON v1 API
- `guia-remision-*` — request/response examples from Guía de Remisión API
- `guia-remision-xml.xml` — sample SUNAT XML generated for Guía de Remisión
- `guia-remision-cdr.xml` — sample SUNAT CDR (Constancia de Recepción) XML response

## Original docs

- API (JSON v1): https://docs.google.com/document/d/1QWWSILBbjd4MDkJl7vCkL2RZvkPh0IC7Wa67BvoYIhA
- Guia de Remision API: https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II
