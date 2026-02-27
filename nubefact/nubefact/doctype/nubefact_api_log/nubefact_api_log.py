# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import get_datetime, now_datetime


class NubefactAPILog(Document):
    def autoname(self):
        timestamp = (
            get_datetime(self.request_timestamp)
            if self.request_timestamp
            else now_datetime()
        )

        self.name = append_number_if_name_exists(
            "Nubefact API Log", timestamp.strftime("%Y%m%d-%H%M%S-%f")
        )


def create_api_log(
    operation: str,
    branch: str,
    api_route: str,
    reference_delivery_note: str | None,
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
) -> str:
    doc = {
        "doctype": "Nubefact API Log",
        "operation": operation,
        "branch": branch,
        "api_route": api_route,
        "reference_delivery_note": reference_delivery_note,
        "reference_invoice": reference_invoice,
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
