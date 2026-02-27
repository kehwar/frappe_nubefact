from __future__ import annotations

from frappe import throw
from frappe.model.document import Document
from frappe.utils import cstr, getdate

from nubefact.utils.nubefact import make_request


def to_nubefact_date(value: str) -> str:
    return getdate(value).strftime("%d-%m-%Y")


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


__all__ = [
    "make_request",
    "to_nubefact_date",
    "require_fields",
    "require_child_fields",
    "format_missing_fields",
    "get_missing_fields",
]
