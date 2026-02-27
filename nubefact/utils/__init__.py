from __future__ import annotations

from typing import Any

from frappe import throw
from frappe.model.document import Document
from frappe.utils import cstr, getdate

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


__all__ = [
    "make_request",
    "to_nubefact_date",
    "set_if_value",
    "omit_empty_values",
    "require_fields",
    "require_child_fields",
    "format_missing_fields",
    "get_missing_fields",
]
