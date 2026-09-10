# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import base64
import binascii
import hashlib
import json
import re
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cstr, get_datetime, now_datetime

MAX_MIGRATION_LOG_TEXT = 2_000
MAX_MIGRATION_LOG_ITEMS = 100
MAX_MIGRATION_LOG_DEPTH = 6
MAX_MIGRATION_LOG_JSON = 32_000
_BASE64_TEXT = re.compile(r"^[A-Za-z0-9+/=\s]+$")
_BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


class NubefactAPILog(Document):
	def autoname(self):
		timestamp = get_datetime(self.request_timestamp) if self.request_timestamp else now_datetime()

		self.name = append_number_if_name_exists("Nubefact API Log", timestamp.strftime("%Y%m%d-%H%M%S-%f"))

	def validate(self):
		if not self.is_new():
			frappe.throw("Los registros API son inmutables y se conservan para auditoría.")
		if not self.flags.get("api_log_controlled_write"):
			frappe.throw("Los registros API sólo pueden ser creados por el servidor.")

	def on_trash(self):
		frappe.throw("Los registros API no se pueden eliminar; consérvelos para auditoría.")


def create_api_log(
	operacion: str,
	local: str,
	ruta_api: str,
	referencia_guia_de_remision: str | None,
	reference_invoice: str | None,
	request_timestamp,
	request_payload: Any,
	response_timestamp,
	response_status_code: int | None,
	response_payload: Any,
	status: str,
	error_code: str | None,
	error_message: str | None,
	duration_ms: int,
	user: str | None = None,
	migration_job: str | None = None,
) -> str:
	if migration_job:
		request_payload = sanitize_migration_log_payload(request_payload)
		response_payload = sanitize_migration_log_payload(response_payload)
		error_message = sanitize_migration_log_text(error_message)
	doc = {
		"doctype": "Nubefact API Log",
		"operacion": operacion,
		"local": local,
		"ruta_api": ruta_api,
		"referencia_guia_de_remision": referencia_guia_de_remision,
		"reference_invoice": reference_invoice,
		"migration_job": migration_job,
		"request_timestamp": request_timestamp,
		"request_payload": _to_json(request_payload),
		"response_timestamp": response_timestamp,
		"response_status_code": response_status_code,
		"response_payload": _to_json(response_payload),
		"status": status,
		"error_code": error_code,
		"error_message": error_message,
		"duration_ms": duration_ms,
	}

	if user:
		doc["owner"] = user

	log = frappe.get_doc(doc)
	log.flags.api_log_controlled_write = True
	log.insert(ignore_permissions=True)
	frappe.db.commit()
	return log.name


def sanitize_migration_log_payload(value: Any) -> dict[str, Any]:
	"""Return bounded audit data without raw artifact or non-object bodies."""

	if not isinstance(value, dict):
		return _value_metadata(value)
	result = _sanitize_object(value, depth=0)
	serialized = json.dumps(result, ensure_ascii=False, default=str)
	if len(serialized.encode("utf-8")) > MAX_MIGRATION_LOG_JSON:
		return {
			"present": True,
			"type": "object",
			"keys": sorted(cstr(key)[:100] for key in value)[:MAX_MIGRATION_LOG_ITEMS],
			"serialized_length": len(serialized),
			"sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
			"truncated": True,
		}
	return result


def sanitize_migration_log_text(value: Any) -> str:
	if value in (None, ""):
		return ""
	text = cstr(value).replace("\x00", "").strip()
	if len(text) > MAX_MIGRATION_LOG_TEXT or _looks_like_base64(text):
		metadata = _value_metadata(text)
		return "Respuesta de error omitida " f"(longitud={metadata['length']}, sha256={metadata['sha256']})."
	return text


def _sanitize_object(value: Any, *, depth: int, key: str = "") -> Any:
	if depth >= MAX_MIGRATION_LOG_DEPTH:
		return _value_metadata(value)
	if isinstance(value, dict):
		result: dict[str, Any] = {}
		for index, (raw_key, child) in enumerate(value.items()):
			if index >= MAX_MIGRATION_LOG_ITEMS:
				result["_truncated_keys"] = len(value) - MAX_MIGRATION_LOG_ITEMS
				break
			child_key = cstr(raw_key)[:200]
			if "base64" in child_key.lower():
				result[child_key] = child if _is_metadata(child) else _value_metadata(child)
			else:
				result[child_key] = _sanitize_object(child, depth=depth + 1, key=child_key)
		return result
	if isinstance(value, list | tuple | set):
		children = list(value)
		result = [
			_sanitize_object(child, depth=depth + 1, key=key) for child in children[:MAX_MIGRATION_LOG_ITEMS]
		]
		if len(children) > MAX_MIGRATION_LOG_ITEMS:
			result.append({"truncated_items": len(children) - MAX_MIGRATION_LOG_ITEMS})
		return result
	if isinstance(value, str):
		if len(value) > MAX_MIGRATION_LOG_TEXT or _looks_like_base64(value) or "base64" in key.lower():
			return _value_metadata(value)
		return value.replace("\x00", "")
	if isinstance(value, bytes):
		return _value_metadata(value)
	if value is None or isinstance(value, bool | int | float):
		return value
	return _value_metadata(value)


def _value_metadata(value: Any) -> dict[str, Any]:
	if value in (None, ""):
		return {"present": False, "type": type(value).__name__, "length": 0, "sha256": ""}
	if isinstance(value, bytes):
		raw = value
		length = len(value)
	elif isinstance(value, str):
		raw = value.encode("utf-8", errors="replace")
		length = len(value)
	else:
		try:
			text = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
		except (TypeError, ValueError):
			text = type(value).__name__
		raw = text.encode("utf-8", errors="replace")
		length = len(text)
	return {
		"present": True,
		"type": type(value).__name__,
		"length": length,
		"encoded_length": length,
		"sha256": hashlib.sha256(raw).hexdigest(),
	}


def _is_metadata(value: Any) -> bool:
	return isinstance(value, dict) and {"present", "encoded_length", "sha256"} <= set(value)


def _looks_like_base64(value: str) -> bool:
	if any(
		fieldname in value.lower() for fieldname in ("pdf_zip_base64", "xml_zip_base64", "cdr_zip_base64")
	):
		return True
	compact = "".join(value.split())
	if len(compact) >= 256 and len(compact) % 4 == 0 and _BASE64_TEXT.fullmatch(compact):
		return True
	for token in _BASE64_TOKEN.findall(value):
		if len(token) % 4:
			continue
		try:
			decoded = base64.b64decode(token, validate=True)
		except (ValueError, binascii.Error):
			continue
		if decoded.startswith((b"PK\x03\x04", b"PK\x05\x06", b"%PDF", b"<?xml", b"<")):
			return True
	return False


def _to_json(value: Any) -> str:
	if value is None:
		return ""

	if isinstance(value, str):
		return value

	try:
		return json.dumps(value, ensure_ascii=False, default=str, indent=2)
	except TypeError:
		return str(value)
