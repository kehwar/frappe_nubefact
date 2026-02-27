# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEFAULT_BASE_URL = "https://api.nubefact.com/api/v1"


class NubefactBranch(Document):
    pass


def _get_branch_doc(branch: str):
    if isinstance(branch, str):
        return frappe.get_doc("Nubefact Branch", branch)

    if getattr(branch, "doctype", None) == "Nubefact Branch":
        return branch

    frappe.throw("Invalid branch. Expected Nubefact Branch name.")


def _build_request_url(route: str | None) -> str:
    if not route:
        frappe.throw("Nubefact Branch Route is required.")

    clean_route = route.strip()
    if clean_route.startswith("http://") or clean_route.startswith("https://"):
        return clean_route

    return f"{DEFAULT_BASE_URL}/{clean_route.lstrip('/')}"


def get_request_config(branch: str) -> tuple[Document, str, str]:
    branch_doc = _get_branch_doc(branch)
    url = _build_request_url(branch_doc.api_route)
    token = branch_doc.get_password("api_token")
    if not token:
        frappe.throw("Nubefact Branch Token is required.")

    return branch_doc, url, token
