# Repository Instructions for GitHub Copilot

## Project Overview

**NubeFact** is a Frappe app that integrates with the [NubeFact](https://www.nubefact.com/) Peruvian electronic invoicing platform for SUNAT compliance. It handles:

- **Facturas / boletas / notas de crédito y débito** — via `nubefact_facturacion` and child tables
- **Guías de remisión** — via `nubefact_guia_de_remision` and child tables
- **API logging** — `nubefact_api_log` records every API call
- **Local/warehouse config** — `nubefact_local` maps Frappe warehouses to NubeFact locals

## Skills

For API client implementation work, load the `nubefact-api-implementation` skill (`.agents/skills/`).

## Build & Test

```bash
bench migrate
bench run-tests --app nubefact
# Omit --site; default site development.localhost is used automatically
```

## Code Quality

```bash
cd apps/nubefact
pre-commit run --all-files
```

Tools enforced: `ruff`, `eslint`, `prettier`, `pyupgrade`.
