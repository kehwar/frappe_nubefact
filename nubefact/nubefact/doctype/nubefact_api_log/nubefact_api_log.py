# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe.model.document import Document


class NubefactAPILog(Document):
    pass


def create_api_log(
    operation: str,
    branch: str,
    api_route: str,
    reference_doctype: str | None,
    reference_name: str | None,
    request_timestamp,
    request_payload: Any,
    response_timestamp,
    response_status_code: int | None,
    response_payload: Any,
    success: int,
    error_code: str | None,
    error_message: str | None,
    duration_ms: int,
    user: str | None = None,
) -> str:
    doc = {
        "doctype": "Nubefact API Log",
        "operation": operation,
        "branch": branch,
        "api_route": api_route,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "request_timestamp": request_timestamp,
        "request_payload": _to_json(request_payload),
        "response_timestamp": response_timestamp,
        "response_status_code": response_status_code,
        "response_payload": _to_json(response_payload),
        "success": success,
        "error_code": error_code,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }

    if user:
        doc["owner"] = user

    log = frappe.get_doc(doc)
    log.insert(ignore_permissions=True)
    frappe.db.commit()
    return log.name


def _to_json(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    try:
        return json.dumps(value, ensure_ascii=False, default=str, indent=2)
    except TypeError:
        return str(value)
