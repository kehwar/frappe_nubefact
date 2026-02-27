# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

DEFAULT_BASE_URL = "https://api.nubefact.com/api/v1"


class NubefactBranch(Document):
    pass


def get_origin_values(branch: str | None) -> dict[str, str | None]:
    branch_doc = frappe.get_doc("Nubefact Branch", branch) if branch else None

    branch_origin_ubigeo = cstr(branch_doc.ubigeo).strip() if branch_doc else None
    branch_origin_address = cstr(branch_doc.address).strip() if branch_doc else None
    branch_origin_sunat_code = (
        cstr(branch_doc.sunat_code).strip() if branch_doc else None
    )

    return {
        "origin_ubigeo": branch_origin_ubigeo,
        "origin_address": branch_origin_address,
        "origin_sunat_code": branch_origin_sunat_code,
    }


def get_last_used_branch_for_user(
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
        "branch": ["is", "set"],
    }

    if exclude_name:
        filters["name"] = ["!=", exclude_name]

    last_branch = frappe.get_all(
        doctype,
        filters=filters,
        pluck="branch",
        order_by="modified desc",
        limit=1,
    )

    return last_branch[0] if last_branch else None


def _build_request_url(route: str | None) -> str:
    if not route:
        frappe.throw("Nubefact Branch Route is required.")

    clean_route = route.strip()
    if clean_route.startswith("http://") or clean_route.startswith("https://"):
        return clean_route

    return f"{DEFAULT_BASE_URL}/{clean_route.lstrip('/')}"


def get_request_config(branch: str) -> tuple[Document, str, str]:
    branch_doc = frappe.get_doc("Nubefact Branch", branch)
    url = _build_request_url(branch_doc.api_route)
    token = branch_doc.get_password("api_token")
    if not token:
        frappe.throw("Nubefact Branch Token is required.")

    return branch_doc, url, token
