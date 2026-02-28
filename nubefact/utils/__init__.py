from __future__ import annotations

import json
from typing import Any

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
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
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


def download_and_attach_file(url: str, filename: str, doctype: str, docname: str):
	"""Descarga un archivo desde una URL y lo adjunta al documento Frappe indicado.

	Si ya existe un adjunto con el mismo nombre en el documento, no se vuelve a descargar.
	Los errores de red se registran en el log de errores de Frappe en lugar de propagarse,
	para no interrumpir el procesamiento de otros documentos.
	"""
	if frappe.db.exists(
		"File",
		{"attached_to_doctype": doctype, "attached_to_name": docname, "file_name": filename},
	):
		return

	try:
		response = requests.get(url, timeout=60)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.log_error(
			title=f"Nubefact: error al descargar el archivo {filename}",
			message=str(exc),
		)
		return

	save_file(
		fname=filename,
		content=response.content,
		dt=doctype,
		dn=docname,
		is_private=1,
	)


def enqueue_nubefact_file_downloads(
	doctype: str, docname: str, title: str, values: dict[str, Any]
):
	"""Encola la descarga de los archivos PDF, XML y CDR si las URLs son válidas.

	Se usa ``enqueue_after_commit=True`` para que los trabajos se encolen sólo después de que
	la transacción actual sea confirmada en la base de datos.
	"""
	file_urls: dict[str, str | None] = {
		"pdf": values.get("enlace_del_pdf"),
		"xml": values.get("enlace_del_xml"),
		"cdr": values.get("enlace_del_cdr"),
	}

	base_name = cstr(title).strip() or cstr(docname).strip()

	for ext, url in file_urls.items():
		if url and isinstance(url, str) and url.startswith(("http://", "https://")):
			filename = f"{base_name}.{ext}"
			frappe.enqueue(
				"nubefact.utils.download_and_attach_file",
				url=url,
				filename=filename,
				doctype=doctype,
				docname=docname,
				queue="short",
				enqueue_after_commit=True,
			)

__all__ = [
	"apply_raw_payload_overrides",
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
