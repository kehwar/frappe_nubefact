# AGENTS.md

## Project

NubeFact is a Frappe app for Peruvian electronic invoicing and SUNAT compliance. Its primary features are:

- Facturas, boletas, credit notes, and debit notes in `nubefact/nubefact/doctype/nubefact_facturacion/`
- Shipping guides in `nubefact/nubefact/doctype/nubefact_guia_de_remision/`
- API request logging in `nubefact/nubefact/doctype/nubefact_api_log/`
- API credentials and establishment data in `nubefact/nubefact/doctype/nubefact_local/`

## References

- Read `references/nubefact-docs/NUBEFACT DOC API JSON V1.md` when changing API payloads, response handling, validation, status polling, or document fields.
- Read `./references/frappe/` when work depends on Frappe Framework behavior, APIs, internals, or conventions.
- Read `./references/press/` when working on or diagnosing how the app is deployed and operated in production.
- Read `./.devcontainer/` and `./DEVELOPMENT.md` when setting up or changing the development container, running end-to-end tests, or using the containerized development site for manual or agent-driven development.

## Validation

Run database migrations after DocType or hook changes:

```bash
bench migrate
```

Run the app test suite:

```bash
bench run-tests --app nubefact
```

Run repository quality checks before completing changes:

```bash
pre-commit run --all-files
```
