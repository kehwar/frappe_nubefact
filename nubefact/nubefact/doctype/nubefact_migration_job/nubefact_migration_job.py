# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import (
	add_to_date,
	cint,
	cstr,
	get_datetime,
	now_datetime,
)

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import import (
	apply_historical_import_payload_to_doc,
)
from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import_xml import (
	parse_import_despatch_xml_payload,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import get_request_config
from nubefact.nubefact.doctype.nubefact_series.nubefact_series import (
	make_gre_artifact_names,
	make_issued_identity_hash,
)
from nubefact.utils import NubefactAPIError, _is_safe_download_url, make_request

from .nubefact_migration_artifacts import (
	ArtifactValidationError,
	InspectedArtifacts,
	canonical_document_identity,
	collect_response_artifacts,
	inspect_zip_container,
)

ACTIVE_STATUSES = {
	"Queued",
	"Querying",
	"Waiting for Artifacts",
	"Downloading",
	"Recreating",
}
TERMINAL_ITEM_STATUSES = {"Created", "Existing", "Not Found", "Warning", "Failed"}
PROTECTED_GRE_STATUSES = {"Aceptada", "Anulación Solicitada", "Anulada"}
CONFLICTING_GRE_STATUSES = {"Borrador", "Enviando", "Error"}
FATAL_PROVIDER_CODES = {"10", "11", "12", "50", "51"}
RETRYABLE_PROVIDER_CODES = {"40"}
LEASE_MINUTES = 15
MAX_RANGE = 1000
MAX_NETWORK_ATTEMPTS = 4
WAIT_DELAYS_SECONDS = (30, 90, 180, 600, 900)
NETWORK_DELAYS_SECONDS = (30, 120, 300)
SERVER_FIELDS = {
	"status",
	"current_number",
	"current_phase",
	"total_count",
	"processed_count",
	"created_count",
	"existing_count",
	"not_found_count",
	"warning_count",
	"failed_count",
	"progress_percent",
	"requested_by",
	"started_at",
	"completed_at",
	"last_error",
	"background_job_id",
	"worker_token",
	"lease_expires_at",
	"next_enqueue_pending",
	"cancel_requested",
	"results",
}
REQUEST_FIELDS = {
	"company",
	"local",
	"nubefact_series",
	"tipo_de_comprobante",
	"serie",
	"from_number",
	"to_number",
}


@dataclass(frozen=True)
class QueryInterpretation:
	kind: str
	response: dict[str, Any]
	message: str = ""
	fatal: bool = False
	retryable: bool = False


class NubefactMigrationJob(Document):
	def autoname(self):
		prefix = f"MIG-GRE-{now_datetime().strftime('%Y')}-"
		self.name = prefix + getseries(f"NubefactMigrationJob::{prefix}", 6)

	def before_validate(self):
		if self.is_new():
			forged = (
				self.status not in (None, "", "Draft")
				or (self.requested_by and self.requested_by != frappe.session.user)
				or bool(self.results)
				or any(
					cint(self.get(fieldname))
					for fieldname in (
						"current_number",
						"processed_count",
						"created_count",
						"existing_count",
						"not_found_count",
						"warning_count",
						"failed_count",
						"progress_percent",
						"next_enqueue_pending",
						"cancel_requested",
					)
				)
				or any(
					self.get(fieldname)
					for fieldname in (
						"current_phase",
						"started_at",
						"completed_at",
						"last_error",
						"background_job_id",
						"worker_token",
						"lease_expires_at",
					)
				)
			)
			if forged:
				frappe.throw("El estado, los contadores y los resultados son administrados por el servidor.")
			self.status = "Draft"
			self.requested_by = frappe.session.user
			self.current_number = 0
			self.current_phase = ""
			self.processed_count = 0
			self.created_count = 0
			self.existing_count = 0
			self.not_found_count = 0
			self.warning_count = 0
			self.failed_count = 0
			self.progress_percent = 0
			self.started_at = None
			self.completed_at = None
			self.last_error = ""
			self.background_job_id = ""
			self.worker_token = ""
			self.lease_expires_at = None
			self.next_enqueue_pending = 0
			self.cancel_requested = 0
			self.set("results", [])
		else:
			self.status = self.status or "Draft"
			self.requested_by = self.requested_by or frappe.session.user
		if self.nubefact_series and self.status == "Draft":
			tracker = frappe.db.get_value(
				"Nubefact Series",
				self.nubefact_series,
				["tipo_de_comprobante", "serie"],
				as_dict=True,
			)
			if tracker:
				self.tipo_de_comprobante = cstr(tracker.tipo_de_comprobante)
				self.serie = cstr(tracker.serie).strip().upper()
		self.title = f"{cstr(self.serie).strip().upper()} {cint(self.from_number)}-{cint(self.to_number)}"
		self.total_count = max(cint(self.to_number) - cint(self.from_number) + 1, 0)

	def validate(self):
		_validate_range(self.from_number, self.to_number)
		if cstr(self.tipo_de_comprobante) != "7":
			frappe.throw("La migración solo admite GRE Remitente tipo 7.")
		self._reject_client_managed_changes()
		self._validate_unique_result_numbers()

	def on_trash(self):
		frappe.throw("Los trabajos de migración no se pueden eliminar; consérvelos para auditoría.")

	def _reject_client_managed_changes(self):
		if self.flags.get("migration_controlled_write"):
			return
		previous = self.get_doc_before_save()
		if not previous:
			if self.status != "Draft" or self.results:
				frappe.throw("El estado y los resultados son administrados por el servidor.")
			return
		if previous.status != "Draft" and any(
			cstr(previous.get(fieldname)) != cstr(self.get(fieldname)) for fieldname in REQUEST_FIELDS
		):
			frappe.throw("Los parámetros de una migración iniciada son inmutables.")
		if any(cstr(previous.get(fieldname)) != cstr(self.get(fieldname)) for fieldname in SERVER_FIELDS):
			frappe.throw("El estado, los contadores y los resultados son administrados por el servidor.")

	def _validate_unique_result_numbers(self):
		numbers = [cint(row.number) for row in self.results or []]
		if len(numbers) != len(set(numbers)):
			frappe.throw("Una migración no puede contener dos resultados para el mismo número.")


def build_consultar_guia_payload(series: str, number: int) -> dict[str, Any]:
	try:
		series, number = canonical_document_identity(series, number)
	except ArtifactValidationError as exc:
		frappe.throw(cstr(exc))
	return {
		"operacion": "consultar_guia",
		"tipo_de_comprobante": 7,
		"serie": series,
		"numero": str(number),
	}


def interpret_query_response(
	response: Any, *, expected_series: str, expected_number: int
) -> QueryInterpretation:
	"""Classify provider errors before enforcing successful-document identity."""

	if not isinstance(response, dict) or not response:
		frappe.throw("NubeFact devolvió una respuesta JSON vacía o inválida.")
	code = response.get("codigo")
	code = cstr(code).strip() if code is not None else ""
	has_error = bool(response.get("errors") or response.get("error") or (code and code != "0"))
	if has_error:
		message = _provider_message(response, code)
		if code == "24":
			return QueryInterpretation("not_found", response, "No existe en NubeFact (código 24).")
		return QueryInterpretation(
			"error",
			response,
			message,
			fatal=code in FATAL_PROVIDER_CODES,
			retryable=code in RETRYABLE_PROVIDER_CODES,
		)

	missing = [
		fieldname
		for fieldname in ("tipo_de_comprobante", "serie", "numero")
		if response.get(fieldname) in (None, "")
	]
	if missing:
		frappe.throw("La respuesta de NubeFact no contiene identidad completa de la GRE.")
	if cstr(response.get("tipo_de_comprobante")).strip() != "7":
		frappe.throw("La respuesta de NubeFact no corresponde a GRE Remitente tipo 7.")
	try:
		actual = canonical_document_identity(response.get("serie"), response.get("numero"))
	except ArtifactValidationError as exc:
		frappe.throw(cstr(exc))
	expected = canonical_document_identity(expected_series, expected_number)
	if actual != expected:
		frappe.throw("La respuesta pertenece a otra serie o número.")

	accepted = _provider_bool(response.get("aceptada_por_sunat"))
	response_code = cstr(response.get("sunat_responsecode") or "").strip()
	soap_error = cstr(response.get("sunat_soap_error") or "").strip()
	if not accepted and (soap_error or (response_code and response_code != "0")):
		return QueryInterpretation(
			"rejected",
			response,
			_provider_message(response, response_code),
		)
	if not accepted:
		return QueryInterpretation("waiting", response, "NubeFact todavía está procesando la GRE.")
	return QueryInterpretation("document", response)


@frappe.whitelist(methods=["POST"])
def create_and_start_migration(
	company: str, local: str, nubefact_series: str, from_number: int, to_number: int
) -> str:
	_require_manager()
	job = frappe.get_doc(
		{
			"doctype": "Nubefact Migration Job",
			"company": company,
			"local": local,
			"nubefact_series": nubefact_series,
			"from_number": cint(from_number),
			"to_number": cint(to_number),
		}
	).insert()
	start_migration(job.name)
	return job.name


@frappe.whitelist(methods=["POST"])
def start_migration(job_name: str) -> None:
	_require_manager()
	job = _lock_job(job_name)
	if job.status in ACTIVE_STATUSES or job.status in {"Completed", "Completed with Warnings"}:
		return
	if job.status != "Draft":
		frappe.throw("Use Reintentar para reabrir un trabajo que ya terminó.")
	_lock_series(job.nubefact_series)
	_validate_start_configuration(job, snapshot=True)
	_assert_no_other_active_job(job)
	now = now_datetime()
	values = {
		"tipo_de_comprobante": "7",
		"serie": cstr(job.serie).strip().upper(),
		"title": f"{cstr(job.serie).strip().upper()} {cint(job.from_number)}-{cint(job.to_number)}",
		"total_count": cint(job.to_number) - cint(job.from_number) + 1,
		"status": "Queued",
		"requested_by": frappe.session.user,
		"started_at": job.started_at or now,
		"completed_at": None,
		"last_error": "",
		"cancel_requested": 0,
		"next_enqueue_pending": 1,
	}
	_set_job_values(job.name, values, update_modified=True, track_history=True)
	frappe.db.commit()
	_dispatch_job(job.name)


@frappe.whitelist(methods=["POST"])
def retry_migration(
	job_name: str,
	*,
	numbers: list[int] | str | None = None,
	include_warnings: bool = False,
	include_not_found: bool = False,
) -> None:
	_require_manager()
	job = _lock_job(job_name)
	if job.status in ACTIVE_STATUSES:
		return
	_lock_series(job.nubefact_series)
	_validate_start_configuration(job)
	_assert_no_other_active_job(job)

	requested = _parse_numbers(numbers)
	rows = frappe.get_all(
		"Nubefact Migration Job Item",
		filters={"parent": job.name},
		fields=["name", "number", "status", "pdf_downloaded", "cdr_downloaded"],
	)
	selected: list[str] = []
	for row in rows:
		number = cint(row.number)
		if requested is not None:
			if number in requested and row.status in {"Failed", "Warning", "Not Found"}:
				selected.append(row.name)
		elif row.status == "Failed":
			selected.append(row.name)
		elif (
			include_warnings
			and row.status == "Warning"
			and (not cint(row.pdf_downloaded) or not cint(row.cdr_downloaded))
		):
			selected.append(row.name)
		elif include_not_found and row.status == "Not Found":
			selected.append(row.name)

	if requested is not None:
		out_of_range = sorted(
			number for number in requested if number < cint(job.from_number) or number > cint(job.to_number)
		)
		if out_of_range:
			frappe.throw(f"Números fuera del rango del trabajo: {', '.join(map(str, out_of_range))}.")

	for item_name in selected:
		frappe.db.set_value(
			"Nubefact Migration Job Item",
			item_name,
			{
				"status": "Pending",
				"artifact_wait_attempts": 0,
				"retry_after": None,
				"completed_at": None,
				"message": "",
			},
			update_modified=False,
		)

	# Cancelled/fatal jobs may have numbers for which no row was ever created.
	if not selected and job.status not in {"Cancelled", "Failed"}:
		return
	_set_job_values(
		job.name,
		{
			"status": "Queued",
			"completed_at": None,
			"last_error": "",
			"cancel_requested": 0,
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 1,
		},
		update_modified=True,
		track_history=True,
	)
	_recompute_counters(job.name)
	frappe.db.commit()
	_dispatch_job(job.name)


@frappe.whitelist(methods=["POST"])
def cancel_migration(job_name: str) -> None:
	_require_manager()
	job = _lock_job(job_name)
	if job.status not in ACTIVE_STATUSES:
		return
	_set_job_values(
		job.name,
		{"cancel_requested": 1, "current_phase": "Cancelación solicitada"},
		update_modified=True,
		track_history=True,
	)
	frappe.db.commit()
	if (
		not job.worker_token
		or not job.lease_expires_at
		or get_datetime(job.lease_expires_at) <= now_datetime()
	):
		_dispatch_job(job.name)


def run_next_migration_number(job_name: str) -> None:
	claim = _claim_next_number(job_name)
	if not claim:
		return
	token, item_name, number = claim
	try:
		_process_claimed_number(job_name, token, item_name, number)
	except OwnershipLost:
		frappe.db.rollback()
	except Exception as exc:
		frappe.db.rollback()
		_safe_fail_item_or_job(job_name, token, item_name, exc)


def recover_stale_migration_jobs() -> None:
	"""Fence and enqueue due active jobs one at a time under their row lock."""

	for job_name in _get_active_job_names():
		job = _lock_job(job_name)
		now = now_datetime()
		if job.status not in ACTIVE_STATUSES or (
			job.worker_token and job.lease_expires_at and get_datetime(job.lease_expires_at) > now
		):
			frappe.db.rollback()
			continue
		number, item = _earliest_nonterminal(job)
		if not number:
			_finalize_job_without_worker(job.name)
			frappe.db.commit()
			continue
		if item and item.retry_after and get_datetime(item.retry_after) > now:
			frappe.db.rollback()
			continue

		# Reserving with a live fencing token prevents concurrent recovery scans
		# from dispatching the same stale job. A failed enqueue is recoverable when
		# this lease expires.
		reservation = uuid.uuid4().hex
		frappe.db.set_value(
			job.doctype,
			job.name,
			{
				"worker_token": reservation,
				"lease_expires_at": add_to_date(now, minutes=LEASE_MINUTES),
				"current_number": number,
				"current_phase": "Recuperando worker interrumpido",
				"next_enqueue_pending": 1,
			},
			update_modified=False,
		)
		frappe.db.commit()
		_dispatch_job(job.name, worker_token=reservation)


def _get_active_job_names() -> list[str]:
	return frappe.get_all(
		"Nubefact Migration Job",
		filters={"status": ["in", sorted(ACTIVE_STATUSES)]},
		pluck="name",
		limit_page_length=0,
	)


def _queued_run_next(migration_job_name: str, worker_token: str | None = None) -> None:
	claim = _claim_next_number(migration_job_name, reserved_token=worker_token)
	if not claim:
		return
	token, item_name, number = claim
	try:
		_process_claimed_number(migration_job_name, token, item_name, number)
	except OwnershipLost:
		frappe.db.rollback()
	except Exception as exc:
		frappe.db.rollback()
		_safe_fail_item_or_job(migration_job_name, token, item_name, exc)


def _claim_next_number(job_name: str, reserved_token: str | None = None) -> tuple[str, str, int] | None:
	job = _lock_job(job_name)
	if job.status not in ACTIVE_STATUSES:
		return None
	now = now_datetime()
	live_lease = bool(job.worker_token and job.lease_expires_at and get_datetime(job.lease_expires_at) > now)
	if reserved_token:
		if not live_lease or cstr(job.worker_token) != cstr(reserved_token):
			frappe.db.rollback()
			return None
	elif live_lease:
		frappe.db.rollback()
		return None
	if cint(job.cancel_requested):
		_mark_cancelled(job)
		frappe.db.commit()
		return None
	try:
		_validate_worker_snapshot(job)
	except Exception as exc:
		_mark_job_fatal(job.name, _safe_message(exc))
		frappe.db.commit()
		return None

	items = {
		cint(row.number): row
		for row in frappe.get_all(
			"Nubefact Migration Job Item",
			filters={"parent": job.name},
			fields=[
				"name",
				"number",
				"status",
				"retry_after",
				"attempts",
				"started_at",
			],
		)
	}
	number, item = _earliest_nonterminal(job, items=items)
	if not number:
		_finalize_job_without_worker(job.name)
		frappe.db.commit()
		return None
	if item and item.retry_after and get_datetime(item.retry_after) > now:
		_schedule_existing_due_job(job.name, get_datetime(item.retry_after))
		frappe.db.commit()
		return None
	if not item:
		item = frappe.get_doc(
			{
				"doctype": "Nubefact Migration Job Item",
				"parent": job.name,
				"parenttype": job.doctype,
				"parentfield": "results",
				"idx": len(items) + 1,
				"number": number,
				"status": "Pending",
			}
		).insert(ignore_permissions=True)

	token = reserved_token or uuid.uuid4().hex
	lease = add_to_date(now, minutes=LEASE_MINUTES)
	frappe.db.set_value(
		"Nubefact Migration Job Item",
		item.name,
		{
			"status": "Querying",
			"attempts": cint(item.attempts) + 1,
			"started_at": item.get("started_at") or now,
			"completed_at": None,
			"retry_after": None,
		},
		update_modified=False,
	)
	_set_job_values(
		job.name,
		{
			"worker_token": token,
			"lease_expires_at": lease,
			"status": "Querying",
			"current_number": number,
			"current_phase": f"Consultando GRE {job.serie}-{number}",
			"next_enqueue_pending": 0,
		},
		update_modified=True,
		track_history=True,
	)
	frappe.db.commit()
	return token, item.name, number


def _earliest_nonterminal(job: Document, *, items: dict[int, Any] | None = None) -> tuple[int, Any | None]:
	if items is None:
		items = {
			cint(row.number): row
			for row in frappe.get_all(
				"Nubefact Migration Job Item",
				filters={"parent": job.name},
				fields=["name", "number", "status", "retry_after", "attempts", "started_at"],
			)
		}
	for number in range(cint(job.from_number), cint(job.to_number) + 1):
		item = items.get(number)
		if not item or item.status not in TERMINAL_ITEM_STATUSES:
			return number, item
	return 0, None


def _process_claimed_number(job_name: str, token: str, item_name: str, number: int) -> None:
	job = frappe.get_doc("Nubefact Migration Job", job_name)
	if _cancel_before_external_request(job_name, token):
		return
	_renew_lease(job_name, token)
	log_names: list[str] = []
	try:
		response = make_request(
			build_consultar_guia_payload(job.serie, number),
			job.local,
			migration_job=job.name,
			log_guard=lambda: _lock_owned_job(job_name, token),
			log_callback=log_names.append,
		)
	except NubefactAPIError as exc:
		_record_api_log(job_name, token, item_name, exc.log_name)
		_handle_request_error(job_name, token, item_name, exc)
		return
	_renew_lease(job_name, token)
	_record_api_log(job_name, token, item_name, log_names[0] if log_names else None)

	interpretation = interpret_query_response(
		response,
		expected_series=job.serie,
		expected_number=number,
	)
	if interpretation.kind == "not_found":
		_complete_item(job_name, token, item_name, "Not Found", interpretation.message)
		return
	if interpretation.kind == "error":
		if interpretation.fatal:
			_mark_fatal_owned(job_name, token, interpretation.message)
		elif interpretation.retryable:
			_handle_retryable(job_name, token, item_name, interpretation.message)
		else:
			_complete_item(job_name, token, item_name, "Failed", interpretation.message)
		return
	if interpretation.kind == "rejected":
		_complete_item(job_name, token, item_name, "Failed", interpretation.message)
		return
	if interpretation.kind == "waiting":
		_wait_for_source_xml(job_name, token, item_name, interpretation.message)
		return

	existing = _resolve_existing_identity(job, number)
	if existing.error:
		_complete_item(
			job_name,
			token,
			item_name,
			"Failed",
			existing.error,
			guia_de_remision=existing.name,
		)
		return

	item_state = frappe.db.get_value(
		"Nubefact Migration Job Item",
		item_name,
		["guia_de_remision", "pdf_downloaded", "xml_downloaded", "cdr_downloaded"],
		as_dict=True,
	)
	attachment_state = (
		_recover_existing_container_artifacts(
			job_name,
			token,
			existing.name,
			job.company,
			job.serie,
			number,
		)
		if existing.name
		else {"pdf": False, "xml": False, "cdr": False}
	)
	is_warning_retry = bool(existing.name and item_state and item_state.guia_de_remision == existing.name)
	if is_warning_retry:
		# Warning retries query consultar_guia for fresh locations, but fetch only
		# the optional artifacts that are still absent.
		requested_kinds = {kind for kind in ("pdf", "cdr") if not attachment_state[kind]}
	elif existing.name:
		requested_kinds = {kind for kind in ("pdf", "xml", "cdr") if not attachment_state[kind]}
	else:
		requested_kinds = {"pdf", "xml", "cdr"}

	if requested_kinds:
		_set_phase(job_name, token, item_name, "Downloading", "Descargando y validando artefactos")
		_renew_lease(job_name, token)
		try:
			artifacts = collect_response_artifacts(
				response,
				expected_series=job.serie,
				expected_number=number,
				kinds=requested_kinds,
				before_request=lambda: _renew_lease(job_name, token),
				after_request=lambda: _renew_lease(job_name, token),
			)
		except ArtifactValidationError as exc:
			# Defensive fallback: collectors normally scope provider errors by kind.
			artifacts = InspectedArtifacts(errors={"xml": _safe_message(exc)})
		_renew_lease(job_name, token)
	else:
		artifacts = InspectedArtifacts()

	if _schedule_transient_artifact_retry(
		job_name,
		token,
		item_name,
		artifacts.retryable_errors & requested_kinds,
	):
		return

	# A compatible local GRE does not need source XML to be recreated. Missing,
	# malformed, or delayed XML is fatal only while the business record is absent.
	if not existing.name and "xml" not in artifacts.logical:
		_wait_for_source_xml(
			job_name,
			token,
			item_name,
			artifacts.errors.get("xml", ""),
		)
		return

	values = _extract_response_values(job, number, response)
	if existing.name:
		gre_name = _merge_existing_gre(job, token, existing.name, number, values)
		base_status = "Existing"
	else:
		_set_phase(job_name, token, item_name, "Recreating", "Reconstruyendo GRE desde XML")
		payload = parse_import_despatch_xml_payload(artifacts.logical["xml"])
		if cstr(payload.get("tipo_de_comprobante")) != "7":
			frappe.throw("El XML no corresponde a GRE Remitente tipo 7.")
		if canonical_document_identity(payload.get("serie"), payload.get("numero")) != (
			canonical_document_identity(job.serie, number)
		):
			frappe.throw("El XML pertenece a otra serie o número.")
		gre_name, was_existing = _create_or_find_gre(job, token, number, payload, values)
		if was_existing:
			gre_name = _merge_existing_gre(job, token, gre_name, number, values)
			base_status = "Existing"
		else:
			base_status = "Created"

	downloads = _attach_artifacts(job_name, token, gre_name, job.company, job.serie, number, artifacts)
	missing_optional = [kind.upper() for kind in ("pdf", "cdr") if not downloads[kind]]
	status = "Warning" if missing_optional else base_status
	message = ""
	if missing_optional:
		message = f"GRE {'creada' if base_status == 'Created' else 'existente'}, pero falta: {', '.join(missing_optional)}."
	_complete_item(
		job_name,
		token,
		item_name,
		status,
		message,
		guia_de_remision=gre_name,
		downloads=downloads,
	)


@dataclass(frozen=True)
class ExistingResolution:
	name: str = ""
	error: str = ""


def _resolve_existing_identity(job: Document, number: int) -> ExistingResolution:
	matches = frappe.get_all(
		"Nubefact Guia De Remision",
		filters={
			"company": job.company,
			"tipo_de_comprobante": "7",
			"serie": job.serie,
			"numero": number,
		},
		fields=["name", "status", "local", "nubefact_series"],
		limit=3,
	)
	if len(matches) > 1:
		return ExistingResolution(
			error="Hay más de una GRE local para esta identidad; corrija los duplicados."
		)
	if not matches:
		return ExistingResolution()
	match = matches[0]
	if match.status in CONFLICTING_GRE_STATUSES:
		return ExistingResolution(
			match.name,
			f"Ya existe una GRE local en estado {match.status} para esta identidad; no se modificó.",
		)
	if match.local != job.local or match.nubefact_series not in (None, "", job.nubefact_series):
		return ExistingResolution(
			match.name, "La GRE local existente pertenece a otro Local o Serie NubeFact."
		)
	return ExistingResolution(match.name)


def _extract_response_values(job: Document, number: int, response: dict[str, Any]) -> dict[str, Any]:
	doc = frappe.new_doc("Nubefact Guia De Remision")
	doc.company = job.company
	doc.local = job.local
	doc.tipo_de_comprobante = "7"
	doc.serie = job.serie
	doc.numero = number
	return doc._extract_response_values(response)


def _create_or_find_gre(
	job: Document,
	token: str,
	number: int,
	payload: dict[str, Any],
	response_values: dict[str, Any],
) -> tuple[str, bool]:
	locked_job = _lock_owned_job(job.name, token)
	_lock_series(job.nubefact_series)
	existing = _resolve_existing_identity(job, number)
	if existing.name or existing.error:
		frappe.db.commit()
		if existing.error:
			frappe.throw(existing.error)
		return existing.name, True

	doc = frappe.new_doc("Nubefact Guia De Remision")
	# Clear source-controlled DocType defaults before applying the signed XML.
	# Absent historical data must never become today's or a current UI default.
	for fieldname in (
		"fecha_de_emision",
		"fecha_de_inicio_de_traslado",
		"cliente_tipo_de_documento",
		"motivo_de_traslado",
		"tipo_de_transporte",
		"peso_bruto_unidad_de_medida",
		"numero_de_bultos",
		"conductor_documento_tipo",
	):
		doc.set(fieldname, None)
	apply_historical_import_payload_to_doc(doc, payload)
	doc.update({key: value for key, value in response_values.items() if doc.meta.has_field(key)})
	doc.update(
		{
			"company": locked_job.company,
			"local": locked_job.local,
			"nubefact_series": locked_job.nubefact_series,
			"tipo_de_comprobante": "7",
			"serie": locked_job.serie,
			"numero": number,
			"migration_job": locked_job.name,
			"migrated_from_nubefact": 1,
			"numero_asignado_automaticamente": 1,
			"issued_identity_hash": make_issued_identity_hash(
				locked_job.company, "7", locked_job.serie, number
			),
		}
	)
	doc.insert(ignore_permissions=True)
	_reconcile_locked_series(job.nubefact_series, number)
	frappe.db.commit()
	return doc.name, False


def _merge_existing_gre(
	job: Document, token: str, gre_name: str, number: int, response_values: dict[str, Any]
) -> str:
	_lock_owned_job(job.name, token)
	rows = frappe.db.sql(
		"SELECT * FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(gre_name,),
		as_dict=True,
	)
	if not rows:
		raise OwnershipLost
	current = rows[0]
	_lock_series(job.nubefact_series)
	if (
		current.company != job.company
		or cstr(current.tipo_de_comprobante) != "7"
		or cstr(current.serie).strip().upper() != job.serie
		or cint(current.numero) != number
		or current.local != job.local
		or current.nubefact_series not in (None, "", job.nubefact_series)
	):
		frappe.throw("La GRE local cambió y ya no es compatible con este trabajo.")

	updates: dict[str, Any] = {}
	for fieldname, value in response_values.items():
		if fieldname in {"numero", "title", "status"} or fieldname.endswith("_zip_base64"):
			continue
		if fieldname == "last_sunat_check" or (
			value not in (None, "") and current.get(fieldname) in (None, "")
		):
			updates[fieldname] = value
	if current.status not in PROTECTED_GRE_STATUSES and response_values.get("status"):
		updates["status"] = response_values["status"]
	if not current.nubefact_series:
		updates["nubefact_series"] = job.nubefact_series
	if not current.issued_identity_hash:
		updates["issued_identity_hash"] = make_issued_identity_hash(job.company, "7", job.serie, number)
	updates["numero_asignado_automaticamente"] = 1
	if updates:
		frappe.db.set_value("Nubefact Guia De Remision", gre_name, updates, update_modified=True)
	_reconcile_locked_series(job.nubefact_series, number)
	frappe.db.commit()
	return gre_name


def _artifact_attachment_state(gre_name: str, company: str, series: str, number: int) -> dict[str, bool]:
	filenames = {
		cstr(name).strip().lower()
		for name in frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Nubefact Guia De Remision",
				"attached_to_name": gre_name,
				"is_private": 1,
			},
			pluck="file_name",
		)
	}
	canonical_names, _ = _migration_artifact_names(company, series, number)
	legacy_names, _ = _legacy_migration_artifact_names(canonical_names, series, number)
	return {
		kind: any(
			any(
				_filename_matches(filename, expected)
				for expected in (canonical_names[kind], *legacy_names[kind])
			)
			for filename in filenames
		)
		for kind in ("pdf", "xml", "cdr")
	}


def _migration_artifact_names(
	company: str, series: str, number: int
) -> tuple[dict[str, str], dict[str, str]]:
	return make_gre_artifact_names(company, "7", series, number)


def _legacy_migration_artifact_names(
	canonical_names: dict[str, str], series: str, number: int
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
	canonical_base = canonical_names["pdf"].rsplit(".", 1)[0]
	identity_prefix = canonical_base.rsplit("-", 1)[0]
	unpadded_base = f"{identity_prefix}-{cint(number)}"
	old_base = f"{cstr(series).strip().upper()}-{cint(number):06d}"
	return (
		{
			"pdf": (f"{unpadded_base}.pdf", f"{old_base}.pdf"),
			"xml": (f"{unpadded_base}.xml", f"{old_base}.xml"),
			"cdr": (f"R-{unpadded_base}.xml", f"{old_base}.cdr"),
		},
		{
			"pdf_zip_base64": (
				f"{unpadded_base}-pdf-field.zip",
				f"{old_base}-pdf-field.zip",
			),
			"xml_zip_base64": (
				f"{unpadded_base}-xml-field.zip",
				f"{old_base}-xml-field.zip",
			),
			"cdr_zip_base64": (
				f"{unpadded_base}-cdr-field.zip",
				f"{old_base}-cdr-field.zip",
			),
		},
	)


def _filename_matches(actual: str, expected: str) -> bool:
	stem, extension = expected.lower().rsplit(".", 1)
	return bool(re.fullmatch(rf"{re.escape(stem)}(?:[0-9a-f]{{6}})*\.{extension}", actual))


def _recover_existing_container_artifacts(
	job_name: str,
	token: str,
	gre_name: str,
	company: str,
	series: str,
	number: int,
) -> dict[str, bool]:
	"""Rebuild missing logical files from previously accepted private ZIP containers."""
	_normalize_existing_artifact_names(job_name, token, gre_name, company, series, number)
	state = _artifact_attachment_state(gre_name, company, series, number)
	missing_kinds = {kind for kind, present in state.items() if not present}
	if not missing_kinds:
		return state

	logical_names, container_names = _migration_artifact_names(company, series, number)
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Nubefact Guia De Remision",
			"attached_to_name": gre_name,
			"is_private": 1,
		},
		fields=["name", "file_name"],
	)
	recovered: dict[str, bytes] = {}
	for row in files:
		filename = cstr(row.file_name).strip().lower()
		if not any(_filename_matches(filename, expected) for expected in container_names.values()):
			continue
		try:
			container = frappe.get_doc("File", row.name).get_content()
			kind, content = inspect_zip_container(
				container,
				expected_series=series,
				expected_number=number,
			)
		except (ArtifactValidationError, FileNotFoundError):
			continue
		if kind not in missing_kinds:
			continue
		if kind in recovered and recovered[kind] != content:
			frappe.throw(f"Hay múltiples contenedores distintos para el artefacto {kind.upper()}.")
		recovered[kind] = content

	for kind, content in recovered.items():
		_save_owned_file(job_name, token, gre_name, logical_names[kind], content)
	return _artifact_attachment_state(gre_name, company, series, number)


def _attach_artifacts(
	job_name: str,
	token: str,
	gre_name: str,
	company: str,
	series: str,
	number: int,
	artifacts: InspectedArtifacts,
) -> dict[str, bool]:
	_normalize_existing_artifact_names(job_name, token, gre_name, company, series, number)
	logical_names, container_names = _migration_artifact_names(company, series, number)
	for kind, content in artifacts.logical.items():
		_save_owned_file(job_name, token, gre_name, logical_names[kind], content)
	for source_field, content in artifacts.containers.items():
		_save_owned_file(job_name, token, gre_name, container_names[source_field], content)
	return _artifact_attachment_state(gre_name, company, series, number)


def _normalize_existing_artifact_names(
	job_name: str,
	token: str,
	gre_name: str,
	company: str,
	series: str,
	number: int,
) -> None:
	_lock_owned_job(job_name, token)
	canonical_names, container_names = _migration_artifact_names(company, series, number)
	legacy_names, legacy_container_names = _legacy_migration_artifact_names(canonical_names, series, number)
	targets = (
		("PDF", canonical_names["pdf"], legacy_names["pdf"]),
		("XML", canonical_names["xml"], legacy_names["xml"]),
		("CDR", canonical_names["cdr"], legacy_names["cdr"]),
		(
			"contenedor PDF",
			container_names["pdf_zip_base64"],
			legacy_container_names["pdf_zip_base64"],
		),
		(
			"contenedor XML",
			container_names["xml_zip_base64"],
			legacy_container_names["xml_zip_base64"],
		),
		(
			"contenedor CDR",
			container_names["cdr_zip_base64"],
			legacy_container_names["cdr_zip_base64"],
		),
	)
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Nubefact Guia De Remision",
			"attached_to_name": gre_name,
			"is_private": 1,
		},
		fields=["name", "file_name", "file_url"],
	)
	for label, canonical_name, compatible_names in targets:
		candidates = [
			row
			for row in files
			if any(
				_filename_matches(cstr(row.file_name).strip().lower(), expected)
				for expected in (canonical_name, *compatible_names)
			)
		]
		if not candidates:
			continue

		readable = []
		missing = []
		for row in candidates:
			try:
				content = frappe.get_doc("File", row.name).get_content()
			except FileNotFoundError:
				missing.append(row)
			else:
				readable.append((row, content))

		# A crash while removing a replaced blob can leave its File row behind.
		# Remove those stale rows before selecting or recreating the canonical file.
		_lock_owned_job(job_name, token)
		for row in missing:
			_remove_replaced_private_file(row)
		if missing:
			frappe.db.commit()
		if not readable:
			continue

		exact = next(
			(
				row
				for row, _content in readable
				if cstr(row.file_name).strip().lower() == canonical_name.lower()
			),
			None,
		)
		source, source_content = next(
			((row, content) for row, content in readable if exact and row.name == exact.name),
			readable[0],
		)
		if any(content != source_content for row, content in readable if row.name != source.name):
			frappe.throw(f"Hay múltiples artefactos {label} distintos para esta GRE.")

		# Commit the canonical copy before deleting any legacy attachment. After
		# a process crash, recovery therefore always has at least one readable copy.
		if not exact:
			_save_owned_file(job_name, token, gre_name, canonical_name, source_content)

		_lock_owned_job(job_name, token)
		for row, _content in readable:
			if not exact or row.name != exact.name:
				_remove_replaced_private_file(row)
		frappe.db.commit()


def _remove_replaced_private_file(file_record: Document) -> None:
	"""Remove one obsolete attachment without deleting a blob shared by another File row."""
	file_doc = frappe.get_doc("File", file_record.name)
	if frappe.db.count("File", {"file_url": file_doc.file_url}) == 1:
		Path(file_doc.get_full_path()).unlink(missing_ok=True)
	frappe.delete_doc("File", file_doc.name, ignore_permissions=True)


def _save_owned_file(job_name: str, token: str, gre_name: str, filename: str, content: bytes):
	_lock_owned_job(job_name, token)
	filters = {
		"attached_to_doctype": "Nubefact Guia De Remision",
		"attached_to_name": gre_name,
		"file_name": filename,
		"is_private": 1,
	}
	if not frappe.db.exists("File", filters):
		file_url = f"/private/files/{filename}"
		conflict = frappe.db.exists("File", {"file_url": file_url})
		if conflict:
			frappe.throw(f"Ya existe otro archivo privado con el nombre canónico {filename}.")
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"content": content,
				"is_private": 1,
				"attached_to_doctype": "Nubefact Guia De Remision",
				"attached_to_name": gre_name,
			}
		)
		# Frappe's file-manager helper always appends a content-hash suffix.
		# Write through File with overwrite=True, then insert the exact private
		# URL so SUNAT identity filenames remain deterministic.
		file_doc.flags.new_file = True
		file_doc.save_file(
			content=content,
			ignore_existing_file_check=True,
			overwrite=True,
		)
		file_doc.flags.copy_from_existing_file = True
		file_doc.insert(ignore_permissions=True)
	frappe.db.commit()


def _wait_for_source_xml(job_name: str, token: str, item_name: str, message: str = ""):
	_lock_owned_job(job_name, token)
	item = frappe.db.get_value(
		"Nubefact Migration Job Item",
		item_name,
		["artifact_wait_attempts"],
		as_dict=True,
	)
	checks = cint(item.artifact_wait_attempts) + 1
	if checks >= 6:
		_complete_item(
			job_name,
			token,
			item_name,
			"Failed",
			"El XML no estuvo disponible después de 30 minutos.",
			artifact_wait_attempts=checks,
		)
		return
	retry_at = add_to_date(now_datetime(), seconds=WAIT_DELAYS_SECONDS[checks - 1])
	_schedule_retry(
		job_name,
		token,
		item_name,
		status="Waiting for Artifacts",
		phase=message or "Esperando que NubeFact publique el XML",
		retry_at=retry_at,
		artifact_wait_attempts=checks,
	)


def _schedule_transient_artifact_retry(
	job_name: str,
	token: str,
	item_name: str,
	retryable_kinds: set[str],
) -> bool:
	if not retryable_kinds:
		return False
	item = frappe.db.get_value(
		"Nubefact Migration Job Item",
		item_name,
		["attempts", "artifact_wait_attempts"],
		as_dict=True,
	)
	network_attempts = max(cint(item.attempts) - cint(item.artifact_wait_attempts), 1)
	if network_attempts >= MAX_NETWORK_ATTEMPTS:
		return False
	retry_at = add_to_date(now_datetime(), seconds=NETWORK_DELAYS_SECONDS[network_attempts - 1])
	_schedule_retry(
		job_name,
		token,
		item_name,
		status="Pending",
		phase=(
			"Reintentando descarga transitoria de: "
			+ ", ".join(sorted(kind.upper() for kind in retryable_kinds))
		),
		retry_at=retry_at,
	)
	return True


def _handle_request_error(job_name: str, token: str, item_name: str, exc: NubefactAPIError) -> None:
	# Transport/authentication classes take precedence over a provider code in a
	# malformed or intermediary-generated HTTP error body.
	if exc.fatal or exc.error_code in FATAL_PROVIDER_CODES or exc.http_status in {401, 403}:
		_mark_fatal_owned(job_name, token, _safe_message(exc))
	elif exc.retryable:
		_handle_retryable(job_name, token, item_name, _safe_message(exc))
	elif exc.error_code == "24":
		_complete_item(job_name, token, item_name, "Not Found", "No existe en NubeFact (código 24).")
	else:
		_complete_item(job_name, token, item_name, "Failed", _safe_message(exc))


def _handle_retryable(job_name: str, token: str, item_name: str, message: str):
	item = frappe.db.get_value(
		"Nubefact Migration Job Item",
		item_name,
		["attempts", "artifact_wait_attempts"],
		as_dict=True,
	)
	network_attempts = max(cint(item.attempts) - cint(item.artifact_wait_attempts), 1)
	if network_attempts >= MAX_NETWORK_ATTEMPTS:
		_complete_item(job_name, token, item_name, "Failed", f"Reintentos agotados: {message}")
		return
	retry_at = add_to_date(now_datetime(), seconds=NETWORK_DELAYS_SECONDS[network_attempts - 1])
	_schedule_retry(
		job_name,
		token,
		item_name,
		status="Pending",
		phase="Reintentando error transitorio de NubeFact",
		retry_at=retry_at,
	)


def _schedule_retry(
	job_name: str,
	token: str,
	item_name: str,
	*,
	status: str,
	phase: str,
	retry_at,
	artifact_wait_attempts: int | None = None,
):
	_lock_owned_job(job_name, token)
	item_values: dict[str, Any] = {"status": status, "retry_after": retry_at, "message": phase}
	if artifact_wait_attempts is not None:
		item_values["artifact_wait_attempts"] = artifact_wait_attempts
	frappe.db.set_value("Nubefact Migration Job Item", item_name, item_values, update_modified=False)
	_set_job_values(
		job_name,
		{
			"status": "Waiting for Artifacts" if status == "Waiting for Artifacts" else "Queued",
			"current_phase": phase,
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 1,
		},
		update_modified=True,
		track_history=True,
	)
	frappe.db.commit()
	_dispatch_job(job_name, enqueue_at=retry_at)


def _complete_item(
	job_name: str,
	token: str,
	item_name: str,
	status: str,
	message: str = "",
	*,
	guia_de_remision: str = "",
	downloads: dict[str, bool] | None = None,
	artifact_wait_attempts: int | None = None,
):
	job = _lock_owned_job(job_name, token)
	values: dict[str, Any] = {
		"status": status,
		"completed_at": now_datetime(),
		"retry_after": None,
		"message": _safe_message(message),
	}
	if guia_de_remision:
		values["guia_de_remision"] = guia_de_remision
	if downloads:
		values.update(
			{
				"pdf_downloaded": cint(downloads.get("pdf")),
				"xml_downloaded": cint(downloads.get("xml")),
				"cdr_downloaded": cint(downloads.get("cdr")),
			}
		)
	if artifact_wait_attempts is not None:
		values["artifact_wait_attempts"] = artifact_wait_attempts
	frappe.db.set_value("Nubefact Migration Job Item", item_name, values, update_modified=False)
	api_log = frappe.db.get_value("Nubefact Migration Job Item", item_name, "api_log")
	if api_log and guia_de_remision:
		frappe.db.set_value(
			"Nubefact API Log",
			api_log,
			"referencia_guia_de_remision",
			guia_de_remision,
			update_modified=False,
		)
	counts = _recompute_counters(job_name)
	if cint(job.cancel_requested):
		parent_values = {
			"status": "Cancelled",
			"completed_at": now_datetime(),
			"current_phase": "Cancelada entre números",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 0,
		}
	elif counts["processed_count"] >= cint(job.total_count):
		parent_values = {
			"status": (
				"Completed with Warnings"
				if counts["warning_count"] or counts["failed_count"]
				else "Completed"
			),
			"completed_at": now_datetime(),
			"current_number": 0,
			"current_phase": "Finalizada",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 0,
		}
	else:
		parent_values = {
			"status": "Queued",
			"current_number": 0,
			"current_phase": "Encolando siguiente número",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 1,
		}
	_set_job_values(job_name, parent_values, update_modified=True, track_history=True)
	frappe.db.commit()
	if parent_values["status"] == "Queued":
		_dispatch_job(job_name)


def _recompute_counters(job_name: str) -> dict[str, int | float]:
	rows = frappe.db.sql(
		"""
		SELECT `status`, COUNT(*) AS `count`
		FROM `tabNubefact Migration Job Item`
		WHERE `parent` = %s
		GROUP BY `status`
		""",
		(job_name,),
		as_dict=True,
	)
	by_status = {row.status: cint(row.count) for row in rows}
	processed = sum(by_status.get(status, 0) for status in TERMINAL_ITEM_STATUSES)
	warning_origins = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN gre.`migration_job` = item.`parent` THEN 1 ELSE 0 END) AS `created`,
			SUM(CASE WHEN gre.`migration_job` IS NULL OR gre.`migration_job` != item.`parent` THEN 1 ELSE 0 END) AS `existing`
		FROM `tabNubefact Migration Job Item` item
		LEFT JOIN `tabNubefact Guia De Remision` gre ON gre.`name` = item.`guia_de_remision`
		WHERE item.`parent` = %s AND item.`status` = 'Warning'
		""",
		(job_name,),
		as_dict=True,
	)[0]
	total = cint(frappe.db.get_value("Nubefact Migration Job", job_name, "total_count"))
	values: dict[str, int | float] = {
		"processed_count": processed,
		"created_count": by_status.get("Created", 0) + cint(warning_origins.created),
		"existing_count": by_status.get("Existing", 0) + cint(warning_origins.existing),
		"not_found_count": by_status.get("Not Found", 0),
		"warning_count": by_status.get("Warning", 0),
		"failed_count": by_status.get("Failed", 0),
		"progress_percent": (processed * 100 / total) if total else 0,
	}
	_set_job_values(job_name, values, update_modified=False, track_history=True)
	return values


def _record_api_log(job_name: str, token: str, item_name: str, log_name: str | None):
	_lock_owned_job(job_name, token)
	if log_name:
		frappe.db.set_value(
			"Nubefact Migration Job Item",
			item_name,
			"api_log",
			log_name,
			update_modified=False,
		)
	frappe.db.commit()


def _renew_lease(job_name: str, token: str):
	_lock_owned_job(job_name, token)
	frappe.db.set_value(
		"Nubefact Migration Job",
		job_name,
		"lease_expires_at",
		add_to_date(now_datetime(), minutes=LEASE_MINUTES),
		update_modified=False,
	)
	frappe.db.commit()


def _set_phase(job_name: str, token: str, item_name: str, status: str, phase: str):
	_lock_owned_job(job_name, token)
	frappe.db.set_value("Nubefact Migration Job Item", item_name, "status", status, update_modified=False)
	_set_job_values(
		job_name,
		{"status": status, "current_phase": phase},
		update_modified=True,
		track_history=True,
	)
	frappe.db.commit()


def _cancel_before_external_request(job_name: str, token: str) -> bool:
	job = _lock_owned_job(job_name, token)
	if not cint(job.cancel_requested):
		frappe.db.rollback()
		return False
	_mark_cancelled(job)
	frappe.db.commit()
	return True


def _mark_cancelled(job: Document):
	_set_job_values(
		job.name,
		{
			"status": "Cancelled",
			"completed_at": now_datetime(),
			"current_phase": "Cancelada entre números",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 0,
		},
		update_modified=True,
		track_history=True,
	)


def _mark_fatal_owned(job_name: str, token: str, message: str):
	_lock_owned_job(job_name, token)
	_mark_job_fatal(job_name, message)
	frappe.db.commit()


def _mark_job_fatal(job_name: str, message: str):
	_set_job_values(
		job_name,
		{
			"status": "Failed",
			"last_error": _safe_message(message),
			"completed_at": now_datetime(),
			"current_phase": "Error fatal",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 0,
		},
		update_modified=True,
		track_history=True,
	)


def _safe_fail_item_or_job(job_name: str, token: str, item_name: str, exc: Exception):
	try:
		if isinstance(exc, frappe.PermissionError | frappe.DoesNotExistError):
			_mark_fatal_owned(job_name, token, exc)
		else:
			_complete_item(job_name, token, item_name, "Failed", _safe_message(exc))
	except OwnershipLost:
		frappe.db.rollback()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			title=f"Nubefact Migration Job: no se pudo registrar error ({job_name})",
			message=frappe.get_traceback(),
		)


def _dispatch_job(job_name: str, enqueue_at=None, worker_token: str | None = None):
	try:
		if enqueue_at and get_datetime(enqueue_at) > now_datetime():
			from frappe.utils.background_jobs import execute_job, get_queue

			method = _queued_run_next
			method_name = f"{method.__module__}.{method.__qualname__}"
			queued = get_queue("long").enqueue_at(
				get_datetime(enqueue_at),
				execute_job,
				kwargs={
					"site": frappe.local.site,
					"user": frappe.session.user,
					"method": method,
					"event": None,
					"job_name": method_name,
					"is_async": True,
					"kwargs": {"migration_job_name": job_name, "worker_token": worker_token},
				},
				job_timeout=900,
			)
		else:
			queued = frappe.enqueue(
				_queued_run_next,
				queue="long",
				migration_job_name=job_name,
				worker_token=worker_token,
			)
		background_job_id = cstr(getattr(queued, "id", "") or getattr(queued, "name", ""))
		job = _lock_job(job_name)
		reservation_still_owned = not worker_token or cstr(job.worker_token) == cstr(worker_token)
		if job.status in ACTIVE_STATUSES and reservation_still_owned:
			frappe.db.set_value(
				job.doctype,
				job.name,
				{"next_enqueue_pending": 0, "background_job_id": background_job_id},
				update_modified=False,
			)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			title=f"Nubefact Migration Job: no se pudo encolar ({job_name})",
			message=frappe.get_traceback(),
		)


def _schedule_existing_due_job(job_name: str, retry_at):
	frappe.db.set_value(
		"Nubefact Migration Job",
		job_name,
		{
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 1,
			"current_phase": "Esperando próximo intento programado",
		},
		update_modified=False,
	)
	# The caller commits before dispatch. Recovery remains the durable fallback.
	frappe.db.after_commit.add(lambda: _dispatch_job(job_name, enqueue_at=retry_at))


def _finalize_job_without_worker(job_name: str):
	counts = _recompute_counters(job_name)
	status = "Completed with Warnings" if counts["warning_count"] or counts["failed_count"] else "Completed"
	_set_job_values(
		job_name,
		{
			"status": status,
			"completed_at": now_datetime(),
			"current_number": 0,
			"current_phase": "Finalizada",
			"worker_token": "",
			"lease_expires_at": None,
			"next_enqueue_pending": 0,
		},
		update_modified=True,
		track_history=True,
	)


def _validate_start_configuration(job: Document, *, snapshot: bool = False):
	_validate_range(job.from_number, job.to_number)
	company = frappe.db.exists("Company", job.company)
	if not company:
		frappe.throw("La compañía seleccionada no existe.")
	company_tax_id = cstr(frappe.db.get_value("Company", job.company, "tax_id")).strip()
	if not re.fullmatch(r"\d{11}", company_tax_id):
		frappe.throw("La compañía debe tener un RUC de 11 dígitos para migrar artefactos GRE.")
	local = frappe.get_doc("Nubefact Local", job.local)
	series = frappe.get_doc("Nubefact Series", job.nubefact_series)
	if local.company != job.company:
		frappe.throw("El Local no pertenece a la compañía seleccionada.")
	if series.company != job.company or series.local != job.local:
		frappe.throw("La Serie NubeFact no pertenece a la compañía y Local seleccionados.")
	if cstr(series.tipo_de_comprobante) != "7":
		frappe.throw("Solo se puede migrar GRE Remitente tipo 7; tipo 8 está fuera de alcance.")
	series_code = cstr(series.serie).strip().upper()
	if not re.fullmatch(r"T[A-Z0-9]{3}", series_code):
		frappe.throw("La serie debe tener formato Txxx con cuatro caracteres válidos.")
	_, url, token = get_request_config(local.name)
	if not cstr(token).strip():
		frappe.throw("El Local no tiene un token API utilizable.")
	_validate_online_route(url)
	if snapshot:
		job.tipo_de_comprobante = "7"
		job.serie = series_code
	elif cstr(job.tipo_de_comprobante) != "7" or cstr(job.serie).strip() != series_code:
		frappe.throw("La identidad de la Serie NubeFact cambió desde que inició la migración.")


def _validate_worker_snapshot(job: Document):
	_validate_start_configuration(job)
	series = frappe.db.get_value(
		"Nubefact Series",
		job.nubefact_series,
		["company", "local", "tipo_de_comprobante", "serie"],
		as_dict=True,
	)
	if not series or any(
		cstr(series.get(fieldname)).strip() != cstr(job.get(fieldname)).strip()
		for fieldname in ("company", "local", "tipo_de_comprobante", "serie")
	):
		frappe.throw("La identidad de la Serie NubeFact cambió desde que inició la migración.")


def _validate_online_route(url: str):
	parsed = urlparse(url)
	host = cstr(parsed.hostname).strip().lower()
	if parsed.scheme not in {"http", "https"} or not host:
		frappe.throw("La ruta API del Local no es válida.")
	if host == "localhost" or host.endswith(".local"):
		frappe.throw("Los Locales Offline/localhost no son compatibles con la migración v1.")
	# Reuse the artifact downloader's DNS and address-family semantics: every
	# resolved address must be globally routable, and credentials are forbidden.
	if not _is_safe_download_url(url):
		frappe.throw(
			"La ruta API debe resolver exclusivamente a direcciones públicas; "
			"los Locales Offline no son compatibles con la migración v1."
		)


def _validate_range(from_number: Any, to_number: Any):
	from_text = cstr(from_number).strip()
	to_text = cstr(to_number).strip()
	if not re.fullmatch(r"\d+", from_text) or not re.fullmatch(r"\d+", to_text):
		frappe.throw("Los límites del rango deben ser enteros.")
	start, end = int(from_text), int(to_text)
	if not 1 <= start <= 99_999_999 or not 1 <= end <= 99_999_999:
		frappe.throw("Los límites del rango deben estar entre 1 y 99,999,999.")
	if end < start:
		frappe.throw("Hasta Número debe ser mayor o igual que Desde Número.")
	if end - start + 1 > MAX_RANGE:
		frappe.throw("Una migración admite como máximo 1,000 números.")


def _assert_no_other_active_job(job: Document):
	other = frappe.db.exists(
		"Nubefact Migration Job",
		{
			"nubefact_series": job.nubefact_series,
			"status": ["in", sorted(ACTIVE_STATUSES)],
			"name": ["!=", job.name],
		},
	)
	if other:
		frappe.throw(f"Ya existe una migración activa para esta Serie NubeFact: {other}.")


def _set_job_values(
	job_name: str,
	values: dict[str, Any],
	*,
	update_modified: bool,
	track_history: bool = False,
) -> None:
	previous = frappe.get_doc("Nubefact Migration Job", job_name) if track_history else None
	frappe.db.set_value(
		"Nubefact Migration Job",
		job_name,
		values,
		update_modified=update_modified,
	)
	if previous:
		current = frappe.get_doc("Nubefact Migration Job", job_name)
		current._doc_before_save = previous
		current.save_version()


def _lock_job(job_name: str) -> Document:
	rows = frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Migration Job` WHERE `name` = %s FOR UPDATE",
		(job_name,),
	)
	if not rows:
		frappe.throw("El trabajo de migración no existe.", frappe.DoesNotExistError)
	return frappe.get_doc("Nubefact Migration Job", job_name)


def _lock_owned_job(job_name: str, token: str) -> Document:
	job = _lock_job(job_name)
	if (
		not cstr(token)
		or cstr(job.worker_token) != cstr(token)
		or not job.lease_expires_at
		or get_datetime(job.lease_expires_at) <= now_datetime()
	):
		raise OwnershipLost
	return job


def _lock_series(series_name: str):
	rows = frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Series` WHERE `name` = %s FOR UPDATE",
		(series_name,),
	)
	if not rows:
		frappe.throw("La Serie NubeFact seleccionada no existe.")


def _reconcile_locked_series(series_name: str, number: int):
	values = frappe.db.get_value(
		"Nubefact Series",
		series_name,
		["numero", "ultimo_numero_asignado"],
		as_dict=True,
	)
	frappe.db.set_value(
		"Nubefact Series",
		series_name,
		{
			"numero": max(cint(values.numero), number + 1),
			"ultimo_numero_asignado": max(cint(values.ultimo_numero_asignado), number),
		},
		update_modified=True,
	)


def _parse_numbers(numbers: list[int] | str | None) -> set[int] | None:
	if numbers in (None, ""):
		return None
	if isinstance(numbers, str):
		try:
			numbers = json.loads(numbers)
		except json.JSONDecodeError:
			frappe.throw("La selección de números no es JSON válido.")
	if not isinstance(numbers, list):
		frappe.throw("La selección de números debe ser una lista.")
	parsed = {cint(number) for number in numbers}
	if not parsed or any(number <= 0 for number in parsed):
		frappe.throw("La selección contiene números inválidos.")
	return parsed


def _provider_bool(value: Any) -> bool:
	return value is True or value == 1 or cstr(value).strip().lower() == "true"


def _provider_message(response: dict[str, Any], code: str = "") -> str:
	message = response.get("errors") or response.get("error")
	if isinstance(message, list):
		message = "; ".join(cstr(value) for value in message)
	if not message:
		message = " - ".join(
			filter(
				None,
				(
					code,
					cstr(response.get("sunat_description") or "").strip(),
					cstr(response.get("sunat_note") or "").strip(),
					cstr(response.get("sunat_soap_error") or "").strip(),
				),
			)
		)
	return _safe_message(message or "NubeFact devolvió un error no reconocido.")


def _safe_message(value: Any) -> str:
	from nubefact.nubefact.doctype.nubefact_api_log.nubefact_api_log import (
		sanitize_migration_log_text,
	)

	text = sanitize_migration_log_text(value)
	for fieldname in ("pdf_zip_base64", "xml_zip_base64", "cdr_zip_base64"):
		if fieldname in text:
			return "NubeFact devolvió un artefacto codificado inválido; revise el API Log sanitizado."
	return text[:1000]


def _require_manager():
	if not ({"Nubefact Manager", "System Manager"} & set(frappe.get_roles())):
		frappe.throw(
			"Solo Nubefact Manager o System Manager puede administrar migraciones.",
			frappe.PermissionError,
		)


class OwnershipLost(Exception):
	"""Raised when a stale worker loses its fencing token."""
