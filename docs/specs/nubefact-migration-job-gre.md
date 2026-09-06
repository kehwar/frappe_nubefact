# Specification: Nubefact Migration Job for Guía de Remisión Remitente

**Status:** Proposed

**Scope:** Guía de Remisión Electrónica Remitente (GRE Remitente, type `7`) only

**Out of scope:** GRE Transportista (type `8`), `Nubefact Facturacion`, invoices, receipts, credit notes, and debit notes

## 1. Problem

A company may begin using this app after it has already issued GREs directly in the NubeFact portal. It may also continue issuing occasional GREs in the portal after adopting the app.

For example, a `Nubefact Series` may be configured to start at number 200 while GREs 1–199 already exist in NubeFact. Those historical documents must be represented locally, with their original PDF, XML, and CDR attached, without issuing them again.

The same mechanism must support later gaps caused by portal issuance. A manager must be able to request:

> For Company A, Local B, Series C, migrate existing NubeFact GRE numbers X through Y.

The operation is asynchronous, observable, retryable, and idempotent.

## 2. Goals

1. Add a `Nubefact Migration Job` DocType from which a manager can request an inclusive number range for one existing GRE Remitente series.
2. Query NubeFact for every number in the range using `consultar_guia` only.
3. Download the original PDF, DespatchAdvice XML, and CDR returned by NubeFact.
4. Recreate missing `Nubefact Guia De Remision` records from the original XML.
5. Preserve NubeFact/SUNAT response metadata and attach all downloaded artifacts privately.
6. Skip numbers that do not exist in NubeFact and skip compatible GREs that already exist locally.
7. Reconcile the selected series counter so an imported number can never be reissued by this app.
8. Make interruption, retry, and repeated overlapping requests safe.

## 3. Non-goals

- The migration must never call `generar_guia` and must never issue a new GRE.
- It does not import GRE Transportista (type `8`) or `Nubefact Facturacion` documents. Transportista support may be specified separately in a later version.
- It does not discover series or number ranges automatically.
- It does not scrape the NubeFact portal.
- It does not infer a later SUNAT cancellation. The documented `consultar_guia` response has no cancellation field, and GRE cancellation is performed directly in SUNAT. A migrated document therefore reflects the status returned by NubeFact; historical cancellation reconciliation remains manual.
- It does not overwrite the business data of an existing local GRE.
- It cannot recover fields absent from the signed source XML and `consultar_guia` response. The query does not return the original `generar_guia` request; API-only values such as email or optional presentation data may therefore remain blank.
- Version 1 supports NubeFact Online/Reseller artifact URLs only. Offline Locals whose artifacts resolve to loopback or private network addresses remain unsupported; weakening the existing SSRF protection is out of scope.

## 4. Existing capabilities to reuse

The implementation must reuse or deepen these existing modules rather than duplicate their rules:

- NubeFact authentication/request logging: `nubefact/utils/nubefact/__init__.py`
- Safe public artifact download and private attachment behavior: `nubefact/utils/__init__.py`
- GRE response interpretation: `NubefactGuiaDeRemision._extract_response_values()`
- UBL `DespatchAdvice` parsing: `nubefact_guia_de_remision_import_xml.py`
- Payload-to-document mapping: `nubefact_guia_de_remision_import.py`
- Series identity and numbering rules: `nubefact_series.py`

The migration orchestrator is the external seam. Its small interface is:

```python
start_migration(job_name: str) -> None
run_next_migration_number(job_name: str) -> None
retry_migration(
    job_name: str,
    *,
    numbers: list[int] | None = None,
    include_warnings: bool = False,
    include_not_found: bool = False,
) -> None
cancel_migration(job_name: str) -> None
recover_stale_migration_jobs() -> None
```

All query, download, XML parsing, idempotency, persistence, series reconciliation, retry, and progress behavior belongs behind that interface.

## 5. User experience

### 5.1 List view

The `Nubefact Migration Job` list has a primary action **Nueva migración GRE Remitente**. It opens a dialog with:

- Company
- Local
- Nubefact Series, filtered to GRE Remitente type `7`
- From Number
- To Number

Submitting the dialog:

1. validates the request on the server;
2. creates the job in `Draft`;
3. invokes `start_migration`;
4. routes the user to the created job.

A job can also be created through its standard form. A draft form has an **Iniciar migración** button.

List columns:

- Status
- Company
- Local
- Series
- Range
- Progress
- Created
- Existing
- Not Found
- Failed
- Modified

List indicators:

- Gray: `Draft`, `Cancelled`
- Blue: `Queued`, `Querying`, `Waiting for Artifacts`, `Downloading`, `Recreating`
- Green: `Completed`
- Orange: `Completed with Warnings`
- Red: `Failed`

### 5.2 Job form

The form shows:

- immutable request parameters after start;
- current number and current phase;
- a progress bar and aggregate counters;
- a result table with one row per processed number;
- links to created/existing GREs and related API logs;
- per-number warning or error details;
- **Cancelar** while active;
- **Reintentar fallidos** when failed results exist;
- **Reintentar artefactos faltantes** when warning results have missing PDF/CDR attachments;
- **Reintentar números seleccionados** for explicitly selected `Failed`, `Warning`, or `Not Found` rows.

The browser never calls NubeFact directly and never receives the Local token.

## 6. Data model

### 6.1 `Nubefact Migration Job`

Naming: by script, `MIG-GRE-{YYYY}-{######}`.

| Field | Type | Required | Behavior |
|---|---|---:|---|
| `title` | Data | generated | `{serie} {from_number}-{to_number}` |
| `company` | Link / Company | yes | Request identity |
| `local` | Link / Nubefact Local | yes | Supplies API route and token |
| `nubefact_series` | Link / Nubefact Series | yes | Must be a GRE Remitente series belonging to Company and Local |
| `tipo_de_comprobante` | Data | yes | Read-only snapshot; always `7` |
| `serie` | Data | yes | Read-only uppercase snapshot |
| `from_number` | Int | yes | Inclusive, 1–99,999,999 |
| `to_number` | Int | yes | Inclusive, greater than or equal to `from_number` |
| `status` | Select | yes | State machine below |
| `current_number` | Int | no | Number currently being processed |
| `current_phase` | Data | no | Concise progress detail |
| `total_count` | Int | yes | `to_number - from_number + 1` |
| `processed_count` | Int | yes | Terminal result rows |
| `created_count` | Int | yes | New local GREs created |
| `existing_count` | Int | yes | Compatible local GREs found |
| `not_found_count` | Int | yes | NubeFact error code 24 |
| `warning_count` | Int | yes | Created/existing but missing optional artifacts |
| `failed_count` | Int | yes | Per-number terminal failures |
| `progress_percent` | Percent | yes | Derived from processed/total |
| `requested_by` | Link / User | yes | User who started the job |
| `started_at` | Datetime | no | First start only |
| `completed_at` | Datetime | no | Terminal transition |
| `last_error` | Long Text | no | Job-level fatal error only |
| `background_job_id` | Data | no | Diagnostic only; not the ownership source of truth |
| `worker_token` | Data | no | Random fencing token held by the current worker |
| `lease_expires_at` | Datetime | no | Durable worker lease; stale leases are recoverable |
| `next_enqueue_pending` | Check | yes | Immediate-dispatch hint; recovery does not depend on it |
| `cancel_requested` | Check | yes | Checked by the worker between numbers |
| `results` | Table / Nubefact Migration Job Item | no | Per-number audit |

Range limit for the first version: **1,000 numbers per job**. Larger migrations must be split into multiple jobs. This keeps the form and child table usable and limits accidental API load.

Request fields and their snapshots cannot change after the job leaves `Draft`.

### 6.2 `Nubefact Migration Job Item` (child table)

This is an implementation/audit child DocType, not a separately navigable business document.

| Field | Type | Behavior |
|---|---|---|
| `number` | Int | Unique within the parent job |
| `status` | Select | `Pending`, `Querying`, `Waiting for Artifacts`, `Downloading`, `Recreating`, `Created`, `Existing`, `Not Found`, `Warning`, `Failed` |
| `guia_de_remision` | Link / Nubefact Guia De Remision | Created or existing target |
| `api_log` | Link / Nubefact API Log | Most recent `consultar_guia` call |
| `attempts` | Int | Total processing attempts |
| `artifact_wait_attempts` | Int | Delayed acceptance/artifact-readiness checks |
| `retry_after` | Datetime | Earliest allowed retry time |
| `pdf_downloaded` | Check | Artifact result |
| `xml_downloaded` | Check | Artifact result; required for creation |
| `cdr_downloaded` | Check | Artifact result |
| `started_at` | Datetime | First attempt |
| `completed_at` | Datetime | Terminal result |
| `message` | Small Text | User-facing warning/error summary |

Rows are added as numbers are attempted; the job does not need to pre-create 1,000 rows.

### 6.3 Related model changes

1. Add optional, read-only, immutable Check `migrated_from_nubefact` and Link `migration_job` to `Nubefact Guia De Remision`.
2. Add hidden unique Data `issued_identity_hash` to `Nubefact Guia De Remision`. It is a SHA-256 of canonical Company + type + Series + Number and is populated only when an identity is claimed by normal allocation or migration; unnumbered/manual drafts keep it null. A patch backfills claimed issued rows and must stop with an actionable report if duplicates already exist.
3. Hide the **Enviar a NubeFact** action for migrated GREs and make `enviar_a_nubefact()` reject them server-side. `consultar_guia` refresh remains allowed unless a manual-void status already forbids it.
4. Add optional read-only Link `migration_job` to `Nubefact API Log` and accept it as an optional argument in `make_request()`/`create_api_log()`.
5. Extend `NubefactAPIError` with HTTP status and retryability metadata required by the worker.
6. Add links from the job to its API logs and migrated GREs.
7. Add `Nubefact Migration Job` to the Workspace under **Monitoreo**.

No token, credential, or Base64 artifact is stored on the job.

## 7. Validation

Starting a job performs all of the following server-side checks:

1. The caller has `Nubefact Manager` or `System Manager`.
2. Company, Local, and Series exist.
3. The Company has an 11-digit RUC in `Company.tax_id`; this RUC supplies the canonical artifact identity.
4. `Nubefact Local.company == job.company`.
5. `Nubefact Series.company == job.company` and `Nubefact Series.local == job.local`.
6. The series type is exactly `7` (GRE Remitente); type `8` is rejected as out of scope.
7. The Series is exactly four valid characters and begins with `T` (`Txxx`).
8. Both range bounds are valid integers and the inclusive range is at most 1,000.
9. The Local has a usable API route and token. The token is checked for presence but is never copied to the job.
10. The Local is an Online/Reseller configuration. Offline/localhost routes are rejected in version 1 because their artifact URLs cannot pass the public-address download policy.
11. There is no other active migration job for the same `Nubefact Series`. Overlapping active jobs are rejected; completed jobs may overlap safely.

The Series values are copied to the read-only snapshots at start. The worker always uses those snapshots and re-verifies that the referenced Series has not changed.

## 8. State machine

```text
Draft -> Queued -> Querying -> Waiting for Artifacts
                    ^                    |
                    |                    v
                    +---- Recreating <- Downloading
                           next number / retry

Any active state -> Cancelled       (between numbers only)
Any active state -> Failed          (fatal job/configuration error)
Any active state -> Completed       (all numbers terminal, no failures/warnings)
Any active state -> Completed with Warnings
```

`Not Found` is an expected per-number outcome and does not by itself make the job a warning or failure.

A job becomes `Completed with Warnings` when every number is terminal but at least one number is `Warning` or `Failed`. A job-level `Failed` is a distinct fatal state reserved for errors that make continuing unsafe, such as invalid credentials, a deleted Local/Series, or a changed identity snapshot.

`Waiting for Artifacts` is nonterminal. An accepted or still-processing GRE whose XML is not ready is checked at elapsed times 0, 30 seconds, 2 minutes, 5 minutes, 15 minutes, and 30 minutes (six checks including the initial query). If XML is still absent at the 30-minute check, the number becomes `Failed`; an explicit retry restarts the wait budget.

Status writes, counters, and result rows are server-managed. Controller validation rejects forged client changes even if a caller bypasses read-only form controls. Worker updates lock the parent row, enforce one result row per number, and recompute counters from child rows.

## 9. Processing algorithm

### 9.1 Queue ownership, chaining, and recovery

- `start_migration` locks the job and then the selected Series row. While holding the Series lock it atomically checks for another active job on that Series, validates/snapshots identity, sets `Queued`, and writes `next_enqueue_pending = 1`. After commit it enqueues `run_next_migration_number(job.name)` on the long queue. This prevents two Draft jobs from winning the active-job check concurrently.
- One worker invocation processes **one source number** and then requests the next invocation. This bounds worker duration, avoids monopolizing a worker for a 1,000-number range, and provides a durable checkpoint after every number.
- A worker first locks the job row and claims it with a random `worker_token` and fifteen-minute `lease_expires_at`. A live lease owned by another token makes a duplicate invocation exit harmlessly. The worker renews the lease immediately before and after every external request. One invocation performs no internal retry loop and makes at most one query plus one attempt for each of the three artifacts, so its bounded work remains within the lease.
- Every persistent side effect—not only job fields—verifies the current token first. GRE/Series writes are performed in a transaction that locks and rechecks the parent job. Each `save_file` call likewise runs while holding the parent job row lock after token/lease validation, so recovery cannot take ownership between the check and file persistence. If lease ownership is lost, the stale worker discards downloaded bytes and exits without writing.
- The next number is the lowest range number without a terminal result. A stale nonterminal item is safe to reclaim because query, creation, Series reconciliation, and attachments are idempotent.
- Finishing one invocation clears its lease and sets `next_enqueue_pending = 1` in the same commit as its checkpoint. The after-commit callback enqueues the next invocation and then clears that signal under lock. The signal may produce duplicate queue messages after a crash, but the lease prevents duplicate owners.
- `recover_stale_migration_jobs()`, scheduled every five minutes, enqueues every active job with an expired/missing lease once the current item's `retry_after` is due, regardless of `next_enqueue_pending`. The flag is an immediate-dispatch hint, not a recovery prerequisite. Recovery also resets stale phase labels for display. Thus crashes before checkpointing or before the next enqueue cannot strand a range or bypass delayed backoff.
- Each external retry is a new delayed invocation, not a sleeping worker. The item stores `retry_after`, and the lease is released before delayed enqueue.
- Retry is allowed from any terminal job state, including `Completed` when selected `Not Found` rows may now exist upstream. It follows the same job-then-Series lock order and atomically rechecks that no other active job owns the Series. It validates requested numbers are in range, resets selected `Failed` rows to `Pending`, optionally reopens warnings with missing PDF/CDR and `Not Found` rows, clears terminal timestamps/errors, transitions the job to `Queued`, and uses the same durable enqueue protocol. Resuming a `Cancelled` job also reopens its unfinished rows. With no `numbers`, all eligible rows selected by the flags are retried. A job-level `Failed` state is revalidated before it resumes. Starting or retrying is otherwise idempotent.
- Cancellation is cooperative and is checked before an external request and before the next number is queued. An in-flight HTTP request is allowed to finish and commit its idempotent result before the job becomes `Cancelled`.

### 9.2 Query NubeFact

For number `N`, call:

```json
{
  "operacion": "consultar_guia",
  "tipo_de_comprobante": 7,
  "serie": "TTT1",
  "numero": "N"
}
```

using the selected Local.

Hard invariant: the migration module can construct only `consultar_guia`; it must not accept an arbitrary operation or arbitrary payload from the browser.

Every call creates a `Nubefact API Log` linked to the migration job. After a target GRE exists, the log is also linked to that GRE. Before persistence, the migration log sanitizer removes all `*_zip_base64` values and records only `{present, encoded_length, sha256}` metadata for them. The API log response shown to a browser is therefore useful for audit without exposing artifact bodies.

Response validation is ordered as follows:

- Require a non-empty JSON object.
- Classify documented top-level provider errors first because error responses, including code `24`, do not carry document identity. Code `24` means `Not Found`. Codes `10`, `11`, `12`, `50`, `51`, and HTTP 401 are job-fatal. Code `40`, HTTP 429, and HTTP 5xx are retryable. Codes `20`, `21`, `22`, and `23` are per-number failures with the provider message retained in sanitized form. Unknown codes are per-number failures unless their HTTP class is retryable or fatal by these rules.
- Only a non-error document response proceeds to strict identity validation and then the existing general response interpreter.
- A document response must explicitly contain type, Series, and number. Returned type and uppercase Series must match the job. Number comparison is canonical numeric comparison, so response `1` and XML ID `T001-00000001` match requested number 1; missing, zero, negative, or non-digit identities are rejected.
- An explicit terminal SUNAT/provider rejection without an XML is a per-number `Failed` result.
- A nonterminal response, or an accepted response whose source XML is not yet available, becomes `Waiting for Artifacts` and follows the delayed readiness schedule in section 8.
- Transient network, HTTP 429, and HTTP 5xx failures are retried up to three times with delayed exponential backoff. `NubefactAPIError` must carry HTTP status/retryability so this classification does not depend on parsing log text. Calls remain sequential; migration never fans out requests to NubeFact.

### 9.3 Resolve an existing local GRE

Before creating anything, look up the business identity:

```text
(company, tipo_de_comprobante, serie, numero)
```

- More than one match is a data-integrity conflict and fails that number.
- A matching `Borrador`, `Enviando`, or locally conflicting `Error` document is not overwritten; fail the number with a link and an actionable message.
- A compatible sent document is retained. Compatibility requires the selected Company and Local, matching identity, and either the selected Series link or no Series link. XML business fields are never applied over it.
- Existing response fields use a dedicated blank-only merge: preserve `Aceptada`, `Anulación Solicitada`, and `Anulada`; never clear a nonblank SUNAT/link field with an empty response; update `last_sunat_check`; and download only missing attachments. Do not call `_save_response_status()` for this merge because that function has overwrite semantics.
- A compatible historical sent document without a tracker claim may be linked to the selected Series and assigned its identity hash under the Series lock; its business fields remain untouched.
- The item ends as `Existing` or `Warning`. If no match exists, proceed with artifact download and recreation.

Concurrency protocol:

- For an existing row, lock GRE first and Series second, matching normal issuance.
- For a missing identity, lock Series, recheck identity without attempting to lock a newly discovered GRE, and insert with the unique `issued_identity_hash`. If the recheck finds a row, release the Series transaction and restart through the existing-row lock order.
- Normal allocation must set the same identity hash while it holds the Series lock. The database uniqueness constraint is the final race guard.
- No network request or artifact download occurs while either row lock is held.

### 9.4 Download and validate assets

Attempt all three logical artifacts before creating a missing GRE:

1. PDF from `enlace_del_pdf` or a Base64 ZIP candidate
2. XML from `enlace_del_xml` or a Base64 ZIP candidate
3. CDR from `enlace_del_cdr` or a Base64 ZIP candidate

URL fields are mapped by name and validated by content. The pinned manuals transpose the prose descriptions of `pdf_zip_base64` and `xml_zip_base64`, so Base64 field labels are not trusted: every nonempty ZIP is content-sniffed and classified by its contained `%PDF` file, UBL `DespatchAdvice`, or receipt `ApplicationResponse`. At most one logical candidate of each type is allowed; byte-identical duplicates are ignored and conflicting duplicates fail the artifact phase.

Requirements:

- Reuse the existing public-address/redirect protections, 60-second timeout, and 100 MiB response limit. Private/loopback artifact URLs are rejected; Offline Locals are unsupported in version 1.
- Do not fetch arbitrary URLs supplied by the user; URLs must come from the NubeFact response.
- Validate the PDF magic bytes when a PDF is returned.
- The source XML is mandatory for recreating a missing GRE. It must use the UBL DespatchAdvice namespace/root and have a canonical identity matching the request. A CDR `ApplicationResponse` is not accepted as the source document.
- All three Base64 fields are treated as ZIP containers. Reject encoded input above 100 MiB, decoded archives above 75 MiB, more than 20 entries, any entry or total uncompressed content above 100 MiB, or a compression ratio above 100:1. Reject encrypted entries, traversal/absolute names, links, and nested archives. Decode and inspect in memory without extracting to disk.
- A classified PDF ZIP must contain exactly one PDF with `%PDF` magic bytes. A source-XML ZIP must contain exactly one matching `DespatchAdvice`. A CDR ZIP must contain exactly one expected receipt file, normally an `ApplicationResponse` XML; preserve every accepted provider container under a filename derived from its source field.
- Logical artifacts use the canonical SUNAT identity built from the selected Company's RUC, GRE Remitente document type `09`, uppercase Series, and an eight-digit zero-padded number: `{ruc}-09-{serie}-{numero:08d}.pdf`, `{ruc}-09-{serie}-{numero:08d}.xml`, and `R-{ruc}-09-{serie}-{numero:08d}.xml` for the CDR. For example, number 2 is stored as `20506005133-09-T001-00000002.pdf`, `20506005133-09-T001-00000002.xml`, and `R-20506005133-09-T001-00000002.xml`. Base64 containers are preserved as `{ruc}-09-{serie}-{numero:08d}-pdf-field.zip`, `{ruc}-09-{serie}-{numero:08d}-xml-field.zip`, and `{ruc}-09-{serie}-{numero:08d}-cdr-field.zip`, even when content classification reveals a transposed PDF/XML field. Newly issued GRE Remitente use the same logical and container naming convention; newly issued GRE Transportista use SUNAT type `31` in place of `09`. The extracted source XML is always attached because it drives reconstruction.
- A retry recognizes prior private unpadded RUC-based names and `{serie}-{six-digit-number}` names, including Frappe collision suffixes, and replaces them with exact eight-digit canonical names without downloading an artifact already present. Public same-name files never satisfy or block the required private attachment.
- A response that is still processing or temporarily lacks XML waits according to section 8 instead of failing immediately.
- PDF or CDR absence/failure after readiness/network retries is non-fatal: create the GRE with the XML and mark the result `Warning`. `retry_migration(..., include_warnings=True)` attempts only missing artifacts.
- Invalid or still-missing XML after the complete readiness budget is fatal for that number and no GRE is created.

The implementation downloads into bounded in-memory buffers for the current number. It does not create public temporary files.

### 9.5 Recreate the GRE from XML

For a missing document:

1. Strictly validate the UBL namespace/root and canonical ID, then parse the original XML with `parse_import_despatch_xml_payload()`. Strengthen the shared parser so a Series has exactly four valid characters, the number is a positive integer, and zero-padding is normalized.
2. Assert the parsed type, uppercase Series, and canonical numeric number against both the query response and job snapshots.
3. Apply the parsed payload through a dedicated historical-import function shared with the existing manual XML importer.
4. Set controlled fields from the job:
   - `company`
   - `local`
   - `nubefact_series`
   - `tipo_de_comprobante`
   - `serie`
   - `numero`
   - `migration_job`
   - `migrated_from_nubefact = 1`
   - `issued_identity_hash`
5. Apply response fields using the same interpretation as `_extract_response_values()`:
   - `status`
   - `aceptada_por_sunat`
   - SUNAT response code/description/note/SOAP error
   - links, QR/hash/barcode values
   - `last_sunat_check`
6. Set `numero_asignado_automaticamente = 1`. For this purpose the flag means the number is claimed by the selected local series tracker and the issued identity is immutable; it does not mean this app originally generated the GRE.
7. Insert using a **controlled historical validation path**. It must validate structure and identity but intentionally bypass issuance-time rules such as “issue date must be today or yesterday.” It must not invent absent historical business values from current Local defaults. Do not expose a generic validation bypass to normal users.
8. Commit the GRE, identity hash, and Series reconciliation in one database transaction.
9. Attach each original artifact privately and idempotently using the deterministic URL/Base64 names in section 9.4.
10. In a final database transaction, link the API log to the GRE and write the terminal item result/counters.

These are intentionally separate transaction boundaries. The existing request/log path commits its API log independently, and file storage cannot roll back atomically with MariaDB/PostgreSQL. A crash may therefore leave a GRE awaiting files or a file awaiting a terminal item status; the lease recovery and deterministic existence checks complete that partial state on retry. The implementation must not claim database/filesystem atomicity.

The original XML attachment is the source of truth for fields that the current parser does not map. Unknown UBL elements are not discarded from the historical record because the signed XML remains attached.

### 9.6 Reconcile the Series

While holding the selected `Nubefact Series` row lock, after a migrated or compatible existing number `N` is confirmed:

```python
series.numero = max(series.numero, N + 1)
series.ultimo_numero_asignado = max(series.ultimo_numero_asignado, N)
```

This preserves a configured starting number. Example: importing 1–199 into a Series whose next number is 200 leaves `numero = 200` and sets `ultimo_numero_asignado >= 199`.

If a portal-issued number is above the current next number, the tracker advances beyond it. The migration never decreases either field.

Normal issuance and migration share the Series lock and `issued_identity_hash` invariant. Existing-row work always locks GRE then Series, as current issuance does. Missing-row migration locks Series only, rechecks identity, and inserts; it never tries to acquire an existing GRE lock while holding Series. No network request or artifact download may occur while a database lock is held.

## 10. Idempotency and retry semantics

- Re-running the same range does not create duplicate GREs or duplicate attachments.
- The identity check uses Company + NubeFact type + Series + Number, not the internal GRE name.
- Artifact attachment checks use target DocType/name, private storage, and the deterministic Company-RUC/SUNAT identity filename. Legacy migration names are normalized on retry.
- A worker crash after creation but before files or the item result are saved is repaired by lease recovery: it finds the compatible GRE, links it, ensures attachments/counter state, and records `Existing` or `Warning`.
- The unique `issued_identity_hash`, populated by both normal allocation and migration, prevents two claimed issued records from winning the same identity race.
- Retrying a `Failed` item increments `attempts` and resumes at the earliest incomplete phase where safe. Retrying a `Warning` only fills missing artifacts. Neither path ever reissues a document.
- `Not Found` is terminal for that job. If the document is later created in the portal, the manager starts a new overlapping job or explicitly retries that number.
- Counters are recomputed from child terminal statuses when a job resumes rather than trusted as the sole source of truth.

## 11. Permissions and audit

| Role | Create/start/cancel/retry | Read |
|---|---:|---:|
| System Manager | yes | yes |
| Nubefact Manager | yes | yes |
| Nubefact User | no | yes |

Additional requirements:

- Whitelisted mutating methods accept POST only and check permission server-side.
- The background worker records `requested_by` but performs controlled writes with explicit permission bypass only inside the migration module.
- All NubeFact queries remain visible in `Nubefact API Log`; Base64 response bodies are replaced by presence/length/hash metadata before the log is saved or returned.
- Job status changes and configuration are tracked in Frappe history.
- `migrated_from_nubefact`, `migration_job`, and `issued_identity_hash` are immutable outside the controlled migration/allocation modules.
- Tokens and Base64 data must not appear in job fields, persisted API-log payloads, messages, exceptions, or browser responses.

## 12. Error behavior

Per-number failures do not stop the range unless they indicate a fatal configuration/account problem.

Examples of per-number messages:

- `No existe en NubeFact (código 24).`
- `La respuesta pertenece a otra serie o número.`
- `El XML no es un DespatchAdvice válido.`
- `Ya existe una GRE local en estado Borrador para esta identidad; no se modificó.`
- `GRE creada, pero no se pudo descargar el CDR.`

A job-level fatal error stores a concise `last_error`; full tracebacks go to Frappe Error Log. The job must not expose credentials or dump Base64 payloads into errors.

## 13. Test plan

### 13.1 Unit tests

1. Validate Company/Local/Series consistency, an 11-digit Company RUC, Online/Reseller policy, type `7` only, `Txxx` Series format, range bounds, range limit, permissions, and immutability after start.
2. Verify exact `consultar_guia` payload construction and prove no migration path can construct `generar_guia`.
3. Classify identity-free code 24 responses as `Not Found` before strict successful-response identity validation, then continue.
4. Classify authentication/account failures as job-fatal and network/429/5xx failures as retryable using structured HTTP metadata.
5. Reject missing/mismatched response identities; accept only canonical numeric zero-padding equivalence.
6. Validate raw artifacts and all three Base64 ZIP paths: size/count/encryption/traversal limits, wrong UBL root/namespace, malformed ZIP, multiple candidate files, and identity mismatch.
7. Recreate type `7` (`Txxx`) GRE Remitente documents from representative real NubeFact XML; reject type `8` responses and XML.
8. Confirm historical dates import while ordinary issuance validations remain enforced.
9. Confirm migrated GREs can be queried but cannot be sent through `generar_guia` from either UI or endpoint.
10. Confirm PDF/XML/CDR are private, deterministic, and not duplicated on retry.
11. Confirm accepted-but-not-ready results use delayed `Waiting for Artifacts`; exhausted XML waits fail; missing PDF/CDR produces retryable `Warning`.
12. Confirm a compatible existing GRE receives only blank response metadata, retains protected statuses/business fields, and is not overwritten.
13. Confirm draft/conflicting and duplicate local identities fail safely.
14. Confirm Series counters only move forward and the 1–199/start-at-200 example remains at 200.
15. Confirm identity-hash uniqueness between normal allocation and migration, including concurrent attempts.
16. Simulate crashes after API-log commit, GRE commit, each attachment, item commit, and before/after next enqueue; prove lease recovery completes without duplicates.
17. Confirm duplicate queue messages are fenced, stale leases recover, and stale workers cannot commit with an old token.
18. Confirm cancellation occurs between numbers and an in-flight result is retained.
19. Confirm counters/progress are recomputed correctly, forged status/result edits are rejected, and final status is deterministic.
20. Confirm API logs link to the job and, after creation, to the GRE; stored/browser-visible payloads contain Base64 presence/length/hash metadata but no Base64 bodies.
21. Confirm terminal jobs reopen correctly for selected failed, warning, cancelled, and later-created `Not Found` numbers.

### 13.2 Integration tests

Mock HTTP at the request seam and use actual DocTypes/database transactions to cover a mixed range:

- one accepted missing GRE;
- one already existing local GRE;
- one NubeFact code 24 gap;
- one missing optional CDR;
- one malformed/mismatched XML.

Expected result: one created, one existing, one not found, two warning/failure outcomes as applicable, no duplicates, and correct Series counters.

### 13.3 Opt-in live demo test

An opt-in test, guarded by the existing `NUBEFACT_E2E_*` environment variables, may:

1. use a dedicated setup helper outside the migration module to generate one uniquely identified GRE Remitente against the configured demo Local/Series or a dedicated random `Txxx` demo series;
2. poll with `consultar_guia` until SUNAT/demo acceptance and artifact links are available;
3. run a one-number migration where no local GRE exists;
4. assert the recreated fields against the generated payload and assert private PDF/XML/CDR attachments.

Generation is test setup only. The migration module is not given access to that helper and remains query-only. This test is never part of the default suite because it creates a persistent external demo document and depends on NubeFact/SUNAT timing.

Commit sanitized real NubeFact XML and `consultar_guia` response fixtures for GRE Remitente type `7`, including delayed/missing-artifact cases. Include negative type `8` fixtures to prove Transportista is rejected. The current handcrafted XML is useful but is not sufficient by itself; the development site already demonstrates that a real NubeFact `DespatchAdvice` can differ in optional nodes.

## 14. Acceptance criteria

1. From the Migration Job list, a manager can request Company + Local + GRE Remitente Series + inclusive range; Transportista Series cannot be selected or started.
2. Saving/starting returns promptly; processing occurs in background jobs.
3. For every existing accepted NubeFact number with valid source XML, exactly one local GRE exists after completion.
4. The GRE is populated from its original NubeFact XML, linked to the selected Company/Local/Series, and contains the NubeFact response status fields.
5. PDF, XML, and CDR are attempted and stored as private attachments (or preserved provider ZIP containers for Base64 fallbacks); extracted source XML is mandatory for a newly created GRE.
6. Missing provider numbers are visibly counted as `Not Found` and do not abort the job.
7. Existing compatible local GREs are not overwritten or duplicated.
8. Re-running or resuming a job is safe and does not duplicate documents or files.
9. The selected Series next number and last-assigned number never decrease and never permit reuse of an imported number.
10. Migration performs only `consultar_guia`; no path calls `generar_guia`, and migrated GREs are non-issuable through the ordinary send endpoint.
11. Progress, per-number outcomes, API logs, waiting/retry state, warnings, and fatal errors are inspectable from the job.
12. Worker crashes and duplicate queue messages are recovered/fenced without stranding or duplicating work.
13. GRE Remitente (type `7`) is supported; GRE Transportista (type `8`) and `Nubefact Facturacion` are rejected as out of scope.
14. `bench migrate`, `bench run-tests --app nubefact`, and `pre-commit run --all-files` pass after implementation.

## 15. Implementation sequence

1. Add DocTypes, permissions, workspace link, fields, identity-hash backfill, and migrations.
2. Add Migration Job linkage to GRE and API Log; make migrated GREs non-issuable.
3. Extract/deepen strict response interpretation, historical XML import, safe artifact fetch/ZIP inspection, and Series identity reconciliation modules.
4. Implement job validation/state transitions and list/form UI.
5. Implement the leased one-number chained worker, readiness/network retries, cancellation, and five-minute stale-job recovery hook.
6. Use the pinned GRE manual export and add sanitized response/XML fixtures plus unit/integration tests.
7. Run an explicit opt-in live demo test only after the mocked suite passes.

## 16. References and verified assumptions

- Repository error-code reference: `references/nubefact-docs/NUBEFACT DOC API JSON V1.md`; SHA-256 `969839fb4f14f8780df3e3d67e3a1eb00ea5d353d4daace934c403ba7b296acf`. Its **Manejo de errores** table defines codes `10`, `11`, `24`, `50`, and `51` and the HTTP status classes used above.
- Pinned GRE manual: `references/nubefact-docs/NUBEFACT GRE API v1.7 2026-09-06.txt`
- The pinned file is the Google Docs plain-text export retrieved on 2026-09-06 from `https://docs.google.com/document/d/1GCmIJNJVmuOD3LC0itdhdTu6260nJBIEmOwFdnIu5II/edit`; SHA-256 `b783936a048edd0af325a1f3f2af18676d6dbb56082b68be103d7c6d6d081b90`.
- The GRE manual defines `consultar_guia` using type, series, and number and returns acceptance fields plus PDF/XML/CDR links or Base64 ZIP values.
- The manual states that accepted GRE assets may take seconds or minutes to become available.
- The manual states that GRE cancellation is performed in SUNAT with Clave SOL; the documented query response does not expose an annulment flag.
- No provider rate limit is documented. This specification therefore requires sequential requests and retry backoff rather than parallel migration.
