from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import frappe
import requests
from filelock import FileLock, Timeout
from frappe import throw
from frappe.model.document import Document
from frappe.utils import cstr, getdate
from frappe.utils.file_manager import save_file

from nubefact.nubefact.doctype.nubefact_series.nubefact_series import make_gre_artifact_names
from nubefact.utils.nubefact import (
	MAX_DUPLICATE_NUMBER_SKIPS,
	NUBEFACT_DUPLICATE_DOCUMENT_ERROR_CODE,
	NubefactAPIError,
	make_request,
)

NUBEFACT_BASE64_FIELDS = (
	"pdf_zip_base64",
	"xml_zip_base64",
	"cdr_zip_base64",
)

_API_LOG_REFERENCE_FIELDS = {
	"Nubefact Facturacion": "reference_invoice",
	"Nubefact Guia De Remision": "referencia_guia_de_remision",
}
_ATTACHMENT_BATCH_EVENT = "nubefact_attachments_ready"
_ATTACHMENT_BATCH_TTL_SECONDS = 60 * 60


def _register_attachment_job_completion(
	batch_id: str | None,
	job_id: str | None,
	job_count: int | None,
	doctype: str,
	docname: str,
) -> None:
	"""Count this job only after its attachment transaction commits."""
	if not batch_id or not job_id or not job_count:
		return

	frappe.db.after_commit.add(
		lambda: _mark_attachment_job_complete(batch_id, job_id, job_count, doctype, docname)
	)


def _mark_attachment_job_complete(
	batch_id: str,
	job_id: str,
	job_count: int,
	doctype: str,
	docname: str,
) -> None:
	"""Publish one realtime event when every job in an attachment batch has committed."""
	cache_key = frappe.cache.make_key(f"nubefact:attachment-batch:{batch_id}")
	try:
		with frappe.cache.pipeline(transaction=True) as pipeline:
			pipeline.sadd(cache_key, job_id)
			pipeline.scard(cache_key)
			pipeline.expire(cache_key, _ATTACHMENT_BATCH_TTL_SECONDS)
			added, completed, _expires = pipeline.execute()
	except Exception:
		frappe.logger("nubefact").exception("Failed to track NubeFact attachment batch completion")
		return

	if added and completed >= job_count:
		frappe.publish_realtime(
			_ATTACHMENT_BATCH_EVENT,
			{"doctype": doctype, "name": docname, "batch_id": batch_id},
			doctype=doctype,
			docname=docname,
		)


def without_nubefact_base64_fields(payload: dict[str, Any]) -> dict[str, Any]:
	"""Return a shallow copy without NubeFact's encoded document artifacts."""
	return {key: value for key, value in payload.items() if key not in NUBEFACT_BASE64_FIELDS}


def to_nubefact_date(value: str) -> str:
	return getdate(value).strftime("%d-%m-%Y")


def set_if_value(payload: dict[str, Any], key: str, value: Any):
	if value is None:
		return
	if isinstance(value, str) and not value.strip():
		return
	if isinstance(value, int | float) and not isinstance(value, bool) and value == 0:
		return

	payload[key] = value


def omit_empty_values(values: dict[str, Any]) -> dict[str, Any]:
	cleaned: dict[str, Any] = {}

	for key, value in values.items():
		set_if_value(cleaned, key, value)

	return cleaned


def require_fields(doc: Document, fields: list[str], message: str):
	missing = get_missing_fields(doc, fields)

	if missing:
		throw(f"{message} Missing: {format_missing_fields(doc, missing)}")


def require_child_fields(row: Document, fields: list[str], message: str):
	missing = get_missing_fields(row, fields)

	if missing:
		throw(f"{message} Missing: {format_missing_fields(row, missing)}")


def format_missing_fields(doc: Document, fieldnames: list[str]) -> str:
	labels: list[str] = []

	for fieldname in fieldnames:
		field = doc.meta.get_field(fieldname)
		labels.append(cstr(field.label).strip() if field and field.label else fieldname)

	return ", ".join(labels)


def get_missing_fields(doc: Document, fields: list[str]) -> list[str]:
	return [
		fieldname
		for fieldname in fields
		if not doc.get(fieldname) or (isinstance(doc.get(fieldname), str) and not doc.get(fieldname).strip())
	]


def apply_raw_payload_overrides(payload: dict[str, Any], raw_value: Any, context: str) -> dict[str, Any]:
	raw_payload = parse_raw_payload(raw_value, context)
	if not raw_payload:
		return payload

	merged_payload = dict(payload)
	merged_payload.update(raw_payload)
	return merged_payload


def parse_raw_payload(raw_value: Any, context: str) -> dict[str, Any]:
	if raw_value in (None, ""):
		return {}

	if isinstance(raw_value, dict):
		return raw_value

	if isinstance(raw_value, str):
		try:
			parsed = json.loads(raw_value)
		except json.JSONDecodeError as exc:
			throw(f"Invalid raw JSON for {context}: {exc.msg}")

		if isinstance(parsed, dict):
			return parsed

	throw(f"Raw payload for {context} must be a JSON object.")
	return {}


def _attachment_exists(doctype: str, docname: str, filename: str, *, private_only: bool = False) -> bool:
	filters = {
		"attached_to_doctype": doctype,
		"attached_to_name": docname,
		"file_name": filename,
	}
	if private_only:
		filters.update(is_private=1, file_url=f"/private/files/{filename}")
	return bool(frappe.db.exists("File", filters))


def _remove_unreferenced_private_blob(file_url: str) -> None:
	if not file_url.startswith("/private/files/") or frappe.db.exists("File", {"file_url": file_url}):
		return
	filename = file_url.removeprefix("/private/files/")
	if filename and Path(filename).name == filename:
		Path(frappe.get_site_path("private", "files", filename)).unlink(missing_ok=True)


def _hold_exact_attachment_lock(filename: str) -> None:
	"""Serialize one canonical path until the surrounding transaction finishes."""
	lock_digest = hashlib.sha256(filename.encode()).hexdigest()
	lock_path = Path(frappe.get_site_path("locks", f"nubefact-artifact-{lock_digest}.lock"))
	lock_path.parent.mkdir(parents=True, exist_ok=True)
	lock = FileLock(lock_path)
	try:
		lock.acquire(timeout=30)
	except Timeout:
		frappe.throw(f"No se pudo bloquear el archivo canónico {filename} para guardarlo.")

	# Keeping the OS lock through commit prevents a second worker from observing
	# the canonical blob before its File row becomes visible. A process crash
	# releases the OS lock even though its harmless lock file remains on disk.
	frappe.db.after_commit.add(lock.release)
	frappe.db.after_rollback.add(lock.release)


def _materialize_canonical_private_blob(source_path: Path, canonical_path: Path, content: bytes) -> None:
	"""Atomically create or adopt an identical crash-left canonical blob."""
	try:
		os.link(source_path, canonical_path)
	except FileExistsError:
		if canonical_path.read_bytes() != content:
			frappe.throw(f"Ya existe otro archivo privado con el nombre canónico {canonical_path.name}.")


def _save_private_attachment_exact(filename: str, content: bytes, doctype: str, docname: str) -> None:
	"""Save one private attachment under its exact logical and physical name."""
	if not filename or Path(filename).name != filename:
		frappe.throw("El nombre canónico del archivo privado no es válido.")

	_hold_exact_attachment_lock(filename)
	if _attachment_exists(doctype, docname, filename, private_only=True):
		return

	file_url = f"/private/files/{filename}"
	canonical_path = Path(frappe.get_site_path("private", "files", filename))
	if frappe.db.exists("File", {"file_url": file_url}):
		frappe.throw(f"Ya existe otro archivo privado con el nombre canónico {filename}.")

	# Use a deterministic staging name while the transaction-scoped lock is held.
	# A retry can remove this path if a crashed worker left it without a File row.
	staging_digest = hashlib.sha256(file_url.encode()).hexdigest()
	staging_filename = f".nubefact-{staging_digest}{Path(filename).suffix}"
	staging_url = f"/private/files/{staging_filename}"
	if frappe.db.exists("File", {"file_url": staging_url}):
		frappe.throw(f"No se pudo preparar el archivo canónico {filename}.")
	_remove_unreferenced_private_blob(staging_url)

	# Insert without an attachment target first. This preserves Frappe's File
	# validation lifecycle while avoiding its non-atomic writes to the canonical
	# name and postponing the attachment comment until the final URL is known.
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": staging_filename,
			"content": content,
			"folder": frappe.db.get_value("File", {"is_attachments_folder": 1}, "name"),
			"is_private": 1,
		}
	)
	file_doc.attached_to_doctype = doctype
	file_doc.attached_to_name = docname
	file_doc.validate_attachment_limit()
	file_doc.attached_to_doctype = None
	file_doc.attached_to_name = None
	file_doc.insert(ignore_permissions=True)

	previous_url = cstr(file_doc.file_url)
	source_path = Path(file_doc.get_full_path())
	stored_content = source_path.read_bytes()
	_materialize_canonical_private_blob(source_path, canonical_path, stored_content)

	# Frappe's insert rollback callback now points at the staging/source URL.
	# Disable it before changing the URL: an interrupted transaction deliberately
	# leaves the canonical blob for an identical retry to adopt safely.
	file_doc.flags.new_file = False
	file_doc.file_name = filename
	file_doc.file_url = file_url
	file_doc.save(ignore_permissions=True)
	_remove_unreferenced_private_blob(previous_url)

	file_doc.attached_to_doctype = doctype
	file_doc.attached_to_name = docname
	file_doc.validate_attachment_limit()
	file_doc.save(ignore_permissions=True)
	file_doc.create_attachment_record()


def attach_nubefact_json(
	payload: dict[str, Any],
	filename: str,
	doctype: str,
	docname: str,
	*,
	attachment_batch_id: str | None = None,
	attachment_job_id: str | None = None,
	attachment_job_count: int | None = None,
) -> None:
	"""Attach a structured issuance payload without encoded response artifacts."""
	try:
		if _attachment_exists(doctype, docname, filename):
			return

		if filename.endswith("-response.json"):
			payload = without_nubefact_base64_fields(payload)
		content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
		save_file(
			fname=filename,
			content=content,
			dt=doctype,
			dn=docname,
			is_private=1,
		)
	finally:
		_register_attachment_job_completion(
			attachment_batch_id,
			attachment_job_id,
			attachment_job_count,
			doctype,
			docname,
		)


def attach_nubefact_base64_file(
	fieldname: str | None = None,
	filename: str | None = None,
	doctype: str | None = None,
	docname: str | None = None,
	*,
	encoded_content: str | None = None,
	exact_filename: bool = False,
	attachment_batch_id: str | None = None,
	attachment_job_id: str | None = None,
	attachment_job_count: int | None = None,
) -> None:
	"""Decode a transient NubeFact Base64 ZIP into a private attachment.

	``fieldname`` remains supported for jobs queued before Base64 DocType fields
	were removed. Those jobs recover the artifact from the purgeable API log.
	"""
	try:
		if not filename or not doctype or not docname:
			return
		if _attachment_exists(doctype, docname, filename, private_only=exact_filename):
			return

		encoded_content = cstr(encoded_content or "")
		if not encoded_content and fieldname:
			encoded_content = _get_logged_base64_artifact(doctype, docname, fieldname)
		if not encoded_content:
			return

		try:
			content = base64.b64decode("".join(encoded_content.split()), validate=True)
		except (ValueError, binascii.Error) as exc:
			frappe.log_error(
				title=f"Nubefact: contenido Base64 inválido para {filename}",
				message=str(exc),
			)
			return

		if exact_filename:
			_save_private_attachment_exact(filename, content, doctype, docname)
		else:
			save_file(
				fname=filename,
				content=content,
				dt=doctype,
				dn=docname,
				is_private=1,
			)
	finally:
		_register_attachment_job_completion(
			attachment_batch_id,
			attachment_job_id,
			attachment_job_count,
			doctype or "",
			docname or "",
		)


def _get_logged_base64_artifact(doctype: str, docname: str, fieldname: str) -> str:
	"""Recover an artifact for jobs queued before its DocType field was removed."""
	if fieldname not in NUBEFACT_BASE64_FIELDS:
		return ""

	if frappe.db.has_column(doctype, fieldname):
		encoded_content = cstr(frappe.db.get_value(doctype, docname, fieldname) or "")
		if encoded_content:
			return encoded_content

	reference_field = _API_LOG_REFERENCE_FIELDS.get(doctype)
	if not reference_field:
		return ""
	logs = frappe.db.sql(
		f"""
			SELECT `response_payload`
			FROM `tabNubefact API Log`
			WHERE `{reference_field}` = %s
				AND `response_payload` LIKE %s
			ORDER BY `request_timestamp` DESC
		""",
		(docname, f'%"{fieldname}"%'),
		as_dict=True,
	)
	for log in logs:
		try:
			payload = json.loads(log.response_payload)
		except (TypeError, json.JSONDecodeError):
			continue
		if isinstance(payload, dict) and payload.get(fieldname):
			return cstr(payload[fieldname])
	return ""


def _is_safe_download_url(url: str) -> bool:
	"""Allow HTTP(S) downloads only when every resolved address is public."""
	parsed = urlparse(url)
	if parsed.scheme not in {"http", "https"} or not parsed.hostname:
		return False
	if parsed.username or parsed.password:
		return False

	try:
		addresses = socket.getaddrinfo(
			parsed.hostname,
			parsed.port or (443 if parsed.scheme == "https" else 80),
			type=socket.SOCK_STREAM,
		)
		return bool(addresses) and all(
			ipaddress.ip_address(address[4][0].split("%", 1)[0]).is_global for address in addresses
		)
	except (OSError, ValueError):
		return False


def _download_public_file(url: str) -> bytes:
	current_url = url
	max_bytes = 100 * 1024 * 1024
	for _redirect in range(4):
		if not _is_safe_download_url(current_url):
			raise requests.RequestException("NubeFact devolvió una URL de descarga no permitida.")

		response = requests.get(current_url, timeout=60, allow_redirects=False, stream=True)
		if response.status_code in {301, 302, 303, 307, 308}:
			location = response.headers.get("Location")
			if not location:
				raise requests.RequestException("La redirección de descarga no contiene una URL.")
			current_url = urljoin(current_url, location)
			continue

		response.raise_for_status()
		try:
			declared_size = int(response.headers.get("Content-Length") or 0)
		except (TypeError, ValueError):
			declared_size = 0
		if declared_size > max_bytes:
			raise requests.RequestException("El archivo de NubeFact supera el límite de 100 MB.")

		content = bytearray()
		for chunk in response.iter_content(chunk_size=1024 * 1024):
			if not chunk:
				continue
			content.extend(chunk)
			if len(content) > max_bytes:
				raise requests.RequestException("El archivo de NubeFact supera el límite de 100 MB.")
		return bytes(content)

	raise requests.TooManyRedirects("La descarga de NubeFact excedió el límite de redirecciones.")


def download_and_attach_file(
	url: str,
	filename: str,
	doctype: str,
	docname: str,
	fallback_content: str | None = None,
	fallback_filename: str | None = None,
	fallback_fieldname: str | None = None,
	*,
	exact_filename: bool = False,
	attachment_batch_id: str | None = None,
	attachment_job_id: str | None = None,
	attachment_job_count: int | None = None,
):
	"""Download a NubeFact artifact and attach it privately to its document.

	If the download fails and NubeFact also returned a Base64 ZIP, use that
	transient value as a fallback. Attachment failures are logged without changing
	issuance state.
	"""
	try:
		if _attachment_exists(doctype, docname, filename, private_only=exact_filename):
			return

		try:
			content = _download_public_file(url)
		except requests.RequestException as exc:
			frappe.log_error(
				title=f"Nubefact: error al descargar el archivo {filename}",
				message=str(exc),
			)
			if (fallback_content or fallback_fieldname) and fallback_filename:
				attach_nubefact_base64_file(
					fieldname=fallback_fieldname,
					filename=fallback_filename,
					doctype=doctype,
					docname=docname,
					encoded_content=fallback_content,
					exact_filename=exact_filename,
				)
			return

		if exact_filename:
			_save_private_attachment_exact(filename, content, doctype, docname)
		else:
			save_file(
				fname=filename,
				content=content,
				dt=doctype,
				dn=docname,
				is_private=1,
			)
	finally:
		_register_attachment_job_completion(
			attachment_batch_id,
			attachment_job_id,
			attachment_job_count,
			doctype,
			docname,
		)


def enqueue_nubefact_file_downloads(
	doctype: str,
	docname: str,
	title: str,
	values: dict[str, Any],
	request_payload: dict[str, Any] | None = None,
	response_payload: dict[str, Any] | None = None,
):
	"""Queue private attachments for a NubeFact issuance response.

	PDF, XML and CDR URLs are downloaded. Their transient Base64 ZIP equivalents
	are used when a URL is absent or its download fails. Issuance request and
	response bodies are stored as JSON, excluding Base64 artifacts from the
	response copy. Jobs run only after commit.
	"""
	base_name = cstr(title).strip() or cstr(docname).strip()
	artifact_names = {
		"pdf": f"{base_name}.pdf",
		"xml": f"{base_name}.xml",
		"cdr": f"{base_name}.cdr",
	}
	container_names = {
		"pdf_zip_base64": f"{base_name}-pdf.zip",
		"xml_zip_base64": f"{base_name}-xml.zip",
		"cdr_zip_base64": f"{base_name}-cdr.zip",
	}
	if doctype == "Nubefact Guia De Remision":
		identity = frappe.db.get_value(
			doctype,
			docname,
			["company", "tipo_de_comprobante", "serie", "numero"],
			as_dict=True,
		)
		if not identity:
			frappe.throw("No se encontró la GRE para nombrar sus artefactos.")
		artifact_names, container_names = make_gre_artifact_names(
			identity.company,
			identity.tipo_de_comprobante,
			identity.serie,
			identity.numero,
		)

	jobs: list[tuple[str, dict[str, Any]]] = []
	json_payloads = {
		"request": request_payload,
		"response": (
			without_nubefact_base64_fields(response_payload) if response_payload is not None else None
		),
	}
	for suffix, payload in json_payloads.items():
		if payload is not None:
			jobs.append(
				(
					"nubefact.utils.attach_nubefact_json",
					{
						"payload": payload,
						"filename": f"{base_name}-{suffix}.json",
						"doctype": doctype,
						"docname": docname,
					},
				)
			)

	exact_artifact_names = doctype == "Nubefact Guia De Remision"
	artifacts = {
		"pdf": (values.get("enlace_del_pdf"), "pdf_zip_base64"),
		"xml": (values.get("enlace_del_xml"), "xml_zip_base64"),
		"cdr": (values.get("enlace_del_cdr"), "cdr_zip_base64"),
	}
	for extension, (url, base64_fieldname) in artifacts.items():
		fallback_filename = container_names[base64_fieldname]
		encoded_content = cstr(values.get(base64_fieldname) or "")
		if isinstance(url, str) and url.startswith(("http://", "https://")):
			job_args = {
				"url": url,
				"filename": artifact_names[extension],
				"doctype": doctype,
				"docname": docname,
				"fallback_content": encoded_content or None,
				"fallback_filename": fallback_filename if encoded_content else None,
			}
			if exact_artifact_names:
				job_args["exact_filename"] = True
			jobs.append(("nubefact.utils.download_and_attach_file", job_args))
		elif encoded_content:
			job_args = {
				"encoded_content": encoded_content,
				"filename": fallback_filename,
				"doctype": doctype,
				"docname": docname,
			}
			if exact_artifact_names:
				job_args["exact_filename"] = True
			jobs.append(("nubefact.utils.attach_nubefact_base64_file", job_args))

	if exact_artifact_names and jobs:
		batch_id = frappe.generate_hash(length=16)
		for index, (_method, job_args) in enumerate(jobs, start=1):
			job_args.update(
				{
					"attachment_batch_id": batch_id,
					"attachment_job_id": f"{index}:{job_args['filename']}",
					"attachment_job_count": len(jobs),
				}
			)

	for method, job_args in jobs:
		frappe.enqueue(
			method,
			**job_args,
			queue="short",
			enqueue_after_commit=True,
		)


__all__ = [
	"MAX_DUPLICATE_NUMBER_SKIPS",
	"NUBEFACT_BASE64_FIELDS",
	"NUBEFACT_DUPLICATE_DOCUMENT_ERROR_CODE",
	"NubefactAPIError",
	"apply_raw_payload_overrides",
	"attach_nubefact_base64_file",
	"attach_nubefact_json",
	"download_and_attach_file",
	"enqueue_nubefact_file_downloads",
	"format_missing_fields",
	"get_missing_fields",
	"make_request",
	"omit_empty_values",
	"parse_raw_payload",
	"require_child_fields",
	"require_fields",
	"set_if_value",
	"to_nubefact_date",
	"without_nubefact_base64_fields",
]
