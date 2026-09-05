# Development

Nubefact includes an app-local Dev Container adapted from the persistent Bench setup in `frappe_soldamundo`.

## Runtime

- Python 3.10.13
- Node 18.20.8
- Yarn 1.22.22
- MariaDB 10.6
- Redis 7
- Frappe and ERPNext version 15, pinned in `.devcontainer/apps.json`

## First start

```bash
cp .devcontainer/.env.example .devcontainer/.env
devcontainer up --workspace-folder .
```

Set `HOST_WORKSPACE_PATH` to this checkout's absolute host path. Set a unique `COMPOSE_PROJECT_NAME` for every clone/worktree; this isolates its persistent Bench and database volumes. Change the example database and Administrator passwords before starting. The installer creates `development.localhost` (or `SITE_NAME`), installs ERPNext and this checkout as the `nubefact` app, enables tests, migrates, and builds assets. It is idempotent and does not start web or scheduler processes.

Container images and Frappe/ERPNext revisions are pinned. Updating a pin is an explicit maintenance change.

## Paths

Inside the developer container:

```text
APP_SOURCE=<absolute host checkout path>
BENCH_ROOT=/workspace/development/frappe-bench
SITE_NAME=development.localhost
```

The checkout is bind-mounted both at `APP_SOURCE` and at `$BENCH_ROOT/apps/nubefact`. Run Git/editing commands from `APP_SOURCE`, and run Bench commands from `BENCH_ROOT`.

## Tests and development server

```bash
cd "$BENCH_ROOT"
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" run-tests --app nubefact
```

Run one module while iterating:

```bash
bench --site "$SITE_NAME" run-tests \
  --module nubefact.nubefact.doctype.nubefact_guia_de_remision.test_nubefact_guia_de_remision
```

### Live demo E2E configuration

Live NubeFact API tests are opt-in. Set `NUBEFACT_E2E_ENABLED=1` and the
`NUBEFACT_E2E_API_URL`/`NUBEFACT_E2E_API_TOKEN` credentials in the ignored
`.devcontainer/.env` file. The same file contains the provider-side local,
SUNAT establishment code, and supported factura, boleta, and shipping-guide
series. Compose passes these values to the developer container.

Do not put credentials in `.devcontainer/.env.example` or run live E2E tests
against a production account. Recreate the developer service after changing
these values so its environment is refreshed:

```bash
docker compose --env-file .devcontainer/.env \
  -f .devcontainer/compose.yaml up -d --force-recreate developer
```

Start the development processes only when needed:

```bash
cd "$BENCH_ROOT"
bench start
```

The site is then available at <http://development.localhost:8000>.

## Persistence and reset

The Bench and MariaDB use Compose-project-specific named Docker volumes. Rebuilding the container preserves them. To reset only this checkout:

```bash
docker compose --env-file .devcontainer/.env \
  -f .devcontainer/compose.yaml down --volumes
```

The scheduler is not running during ordinary test commands, so GRE polling cannot call external services unexpectedly.
