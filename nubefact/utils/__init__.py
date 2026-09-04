from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import frappe
import requests
from frappe import throw
from frappe.model.document import Document
from frappe.utils import cstr, getdate
from frappe.utils.file_manager import save_file

from nubefact.utils.nubefact import make_request


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
        if not doc.get(fieldname)
        or (isinstance(doc.get(fieldname), str) and not doc.get(fieldname).strip())
    ]


def apply_raw_payload_overrides(
    payload: dict[str, Any], raw_value: Any, context: str
) -> dict[str, Any]:
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


def _attachment_exists(doctype: str, docname: str, filename: str) -> bool:
	return bool(
		frappe.db.exists(
			"File",
			{
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"file_name": filename,
			},
		)
	)


def attach_nubefact_json(
	payload: dict[str, Any], filename: str, doctype: str, docname: str
) -> None:
	"""Attach the exact structured payload used for a successful issue request."""
	if _attachment_exists(doctype, docname, filename):
		return

	content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
	save_file(
		fname=filename,
		content=content,
		dt=doctype,
		dn=docname,
		is_private=1,
	)


def attach_nubefact_base64_file(
	fieldname: str, filename: str, doctype: str, docname: str
) -> None:
	"""Decode one of NubeFact's ``*_zip_base64`` fields into a private attachment."""
	if _attachment_exists(doctype, docname, filename):
		return

	encoded_content = cstr(frappe.db.get_value(doctype, docname, fieldname) or "")
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

	save_file(
		fname=filename,
		content=content,
		dt=doctype,
		dn=docname,
		is_private=1,
	)


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
			ipaddress.ip_address(address[4][0].split("%", 1)[0]).is_global
			for address in addresses
		)
	except (OSError, ValueError):
		return False


def _download_public_file(url: str) -> bytes:
	current_url = url
	for _redirect in range(4):
		if not _is_safe_download_url(current_url):
			raise requests.RequestException("NubeFact devolvió una URL de descarga no permitida.")

		response = requests.get(current_url, timeout=60, allow_redirects=False)
		if response.status_code in {301, 302, 303, 307, 308}:
			location = response.headers.get("Location")
			if not location:
				raise requests.RequestException("La redirección de descarga no contiene una URL.")
			current_url = urljoin(current_url, location)
			continue

		response.raise_for_status()
		content = response.content
		if len(content) > 100 * 1024 * 1024:
			raise requests.RequestException("El archivo de NubeFact supera el límite de 100 MB.")
		return content

	raise requests.TooManyRedirects("La descarga de NubeFact excedió el límite de redirecciones.")


def download_and_attach_file(
	url: str,
	filename: str,
	doctype: str,
	docname: str,
	fallback_fieldname: str | None = None,
	fallback_filename: str | None = None,
):
	"""Download a NubeFact artifact and attach it privately to its document.

	If the download fails and NubeFact also returned a Base64 ZIP, use that value
	as a fallback. Attachment failures are logged without changing issuance state.
	"""
	if _attachment_exists(doctype, docname, filename):
		return

	try:
		content = _download_public_file(url)
	except requests.RequestException as exc:
		frappe.log_error(
			title=f"Nubefact: error al descargar el archivo {filename}",
			message=str(exc),
		)
		if fallback_fieldname and fallback_filename:
			attach_nubefact_base64_file(
				fallback_fieldname, fallback_filename, doctype, docname
			)
		return

	save_file(
		fname=filename,
		content=content,
		dt=doctype,
		dn=docname,
		is_private=1,
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

	PDF, XML and CDR URLs are downloaded. Their Base64 ZIP equivalents are used
	when a URL is absent or its download fails. The complete issuance request and
	response bodies are also stored as JSON. Jobs run only after commit.
	"""
	base_name = cstr(title).strip() or cstr(docname).strip()

	json_payloads = {
		"request": request_payload,
		"response": response_payload,
	}
	for suffix, payload in json_payloads.items():
		if payload is not None:
			frappe.enqueue(
				"nubefact.utils.attach_nubefact_json",
				payload=payload,
				filename=f"{base_name}-{suffix}.json",
				doctype=doctype,
				docname=docname,
				queue="short",
				enqueue_after_commit=True,
			)

	artifacts = {
		"pdf": (values.get("enlace_del_pdf"), "pdf_zip_base64"),
		"xml": (values.get("enlace_del_xml"), "xml_zip_base64"),
		"cdr": (values.get("enlace_del_cdr"), "cdr_zip_base64"),
	}
	for extension, (url, base64_fieldname) in artifacts.items():
		fallback_filename = f"{base_name}-{extension}.zip"
		if isinstance(url, str) and url.startswith(("http://", "https://")):
			frappe.enqueue(
				"nubefact.utils.download_and_attach_file",
				url=url,
				filename=f"{base_name}.{extension}",
				doctype=doctype,
				docname=docname,
				fallback_fieldname=base64_fieldname if values.get(base64_fieldname) else None,
				fallback_filename=fallback_filename if values.get(base64_fieldname) else None,
				queue="short",
				enqueue_after_commit=True,
			)
		elif values.get(base64_fieldname):
			frappe.enqueue(
				"nubefact.utils.attach_nubefact_base64_file",
				fieldname=base64_fieldname,
				filename=fallback_filename,
				doctype=doctype,
				docname=docname,
				queue="short",
				enqueue_after_commit=True,
			)

__all__ = [
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
]
