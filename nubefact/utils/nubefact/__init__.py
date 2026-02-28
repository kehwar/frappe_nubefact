from __future__ import annotations

import time
from typing import Any

import frappe
import requests
from frappe.utils import now_datetime

from nubefact.nubefact.doctype.nubefact_api_log.nubefact_api_log import create_api_log
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import get_request_config


def make_request(
    payload: dict[str, Any],
    local: str,
    referencia_guia_de_remision: str | None = None,
    reference_invoice: str | None = None,
    timeout: int = 60,
) -> Any:
    if not isinstance(payload, dict):
        frappe.throw("El payload de Nubefact debe ser un diccionario.")

    operacion = payload.get("operacion")
    if not operacion:
        frappe.throw("La operación es obligatoria en el campo 'operacion' del payload.")

    if not local:
        frappe.throw("El local es obligatorio para llamar a la API de Nubefact.")

    local_doc, url, token = get_request_config(local)

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
            "OK" if response.ok and not _has_api_error(response_payload) else "Error"
        )
        if status == "Error":
            error_code, error_message = _extract_error_details(response_payload)
            if not error_message:
                error_message = f"La solicitud a Nubefact falló con código de estado {response_status_code}."

    except requests.RequestException as exc:
        error_message = str(exc)
        status = "Error"
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        response_timestamp = now_datetime()
        log_name = create_api_log(
            operacion=operacion,
            local=local_doc.name,
            ruta_api=url,
            referencia_guia_de_remision=referencia_guia_de_remision,
            reference_invoice=reference_invoice,
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
        frappe.throw(
            error_message or "La solicitud a Nubefact falló.",
            title=f"Error de Nubefact (Log: {log_name})",
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


__all__ = ["make_request"]
