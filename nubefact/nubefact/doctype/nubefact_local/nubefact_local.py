# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

DEFAULT_BASE_URL = "https://api.nubefact.com/api/v1"


class NubefactLocal(Document):
    pass


def get_origin_values(local: str | None) -> dict[str, str | None]:
    local_doc = frappe.get_doc("Nubefact Local", local) if local else None

    local_origin_ubigeo = cstr(local_doc.ubigeo).strip() if local_doc else None
    local_origin_address = cstr(local_doc.direccion).strip() if local_doc else None
    local_origin_sunat_code = (
        cstr(local_doc.codigo_sunat).strip() if local_doc else None
    )

    return {
        "origin_ubigeo": local_origin_ubigeo,
        "origin_address": local_origin_address,
        "origin_sunat_code": local_origin_sunat_code,
    }


def get_last_used_local_for_user(
    *, doctype: str, user: str | None = None, exclude_name: str | None = None
) -> str | None:
    if not cstr(doctype).strip():
        frappe.throw("DocType is required.")

    if doctype not in ("Nubefact Delivery Note", "Nubefact Invoice"):
        frappe.throw(
            "Unsupported DocType. Expected 'Nubefact Delivery Note' or 'Nubefact Invoice'."
        )

    filters = {
        "owner": cstr(user or frappe.session.user).strip(),
        "local": ["is", "set"],
    }

    if exclude_name:
        filters["name"] = ["!=", exclude_name]

    last_local = frappe.get_all(
        doctype,
        filters=filters,
        pluck="local",
        order_by="modified desc",
        limit=1,
    )

    return last_local[0] if last_local else None


def _build_request_url(route: str | None) -> str:
    if not route:
        frappe.throw("Nubefact Local Route is required.")

    clean_route = route.strip()
    if clean_route.startswith("http://") or clean_route.startswith("https://"):
        return clean_route

    return f"{DEFAULT_BASE_URL}/{clean_route.lstrip('/')}"


def get_request_config(local: str) -> tuple[Document, str, str]:
    local_doc = frappe.get_doc("Nubefact Local", local)
    url = _build_request_url(local_doc.ruta_api)
    token = local_doc.get_password("token_api")
    if not token:
        frappe.throw("Nubefact Local Token is required.")

    return local_doc, url, token
