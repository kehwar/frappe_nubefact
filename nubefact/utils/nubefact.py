from __future__ import annotations

import time
from typing import Any

import frappe
import requests
from frappe.utils import now_datetime

from nubefact.nubefact.doctype.nubefact_api_log.nubefact_api_log import create_api_log
from nubefact.nubefact.doctype.nubefact_branch.nubefact_branch import get_request_config


def make_request(
    payload: dict[str, Any],
    branch: str,
    operation: str | None = None,
    reference_delivery_note: str | None = None,
    timeout: int = 60,
    silent: bool = False,
) -> Any:
    if not isinstance(payload, dict):
        if silent:
            return None
        frappe.throw("Nubefact payload must be a dict.")

    operation = operation or payload.get("operacion")
    if not operation:
        if silent:
            return None
        frappe.throw(
            "Operation is required. Pass operation=... or include 'operacion' in payload."
        )

    if not branch:
        if silent:
            return None
        frappe.throw("Branch is required to call Nubefact API.")

    branch_doc, url, token = get_request_config(branch)

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    request_timestamp = now_datetime()
    start = time.perf_counter()

    response_status_code: int | None = None
    response_payload: Any = None
    error_code: str | None = None
    error_message: str | None = None
    status = "Error"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response_status_code = response.status_code

        try:
            response_payload = response.json()
        except ValueError:
            response_payload = response.text

        status = (
            "Success"
            if response.ok and not _has_api_error(response_payload)
            else "Error"
        )
        if status == "Error":
            error_code, error_message = _extract_error_details(response_payload)
            if not error_message:
                error_message = (
                    f"Nubefact request failed with status code {response_status_code}."
                )

    except requests.RequestException as exc:
        error_message = str(exc)
        status = "Error"
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        response_timestamp = now_datetime()
        log_name = create_api_log(
            operation=operation,
            branch=branch_doc.name,
            api_route=url,
            reference_delivery_note=reference_delivery_note,
            request_timestamp=request_timestamp,
            request_payload=payload,
            response_timestamp=response_timestamp,
            response_status_code=response_status_code,
            response_payload=response_payload,
            status=status,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    if status == "Error":
        if silent:
            return None
        frappe.throw(
            error_message or "Nubefact request failed.",
            title=f"Nubefact Error (Log: {log_name})",
        )

    return response_payload


def _has_api_error(response_payload: Any) -> bool:
    if not isinstance(response_payload, dict):
        return False

    if response_payload.get("errors"):
        return True

    if response_payload.get("error"):
        return True

    return False


def _extract_error_details(response_payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(response_payload, dict):
        return None, str(response_payload) if response_payload else None

    error_code = response_payload.get("codigo")
    error_message = response_payload.get("errors") or response_payload.get("error")

    if isinstance(error_message, list):
        error_message = "\n".join(str(item) for item in error_message)

    if error_code is not None:
        error_code = str(error_code)

    if error_message is not None:
        error_message = str(error_message)

    return error_code, error_message
