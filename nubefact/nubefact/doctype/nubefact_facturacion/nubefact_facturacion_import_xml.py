from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import frappe
from frappe.utils import cstr


def parse_import_cpe_xml_payload(text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        frappe.throw("Formato XML inválido.")

    root_name = _xml_local_name(root.tag)
    if root_name == "ApplicationResponse":
        frappe.throw(
            "El XML CDR no se puede usar para crear un comprobante. Use XML del documento emitido."
        )
    if root_name != "DespatchAdvice":
        frappe.throw("Tipo de XML no soportado. Se esperaba XML SUNAT DespatchAdvice.")

    return _parse_despatch_advice_payload(root)


def _parse_despatch_advice_payload(root: ET.Element) -> dict[str, Any]:
    full_number = _xml_get_nested_text(root, ["ID"])
    series, number = _split_series_number(full_number)
    customer_id_node = _xml_get_nested_node(
        root,
        ["DeliveryCustomerParty", "Party", "PartyIdentification", "ID"],
    )

    payload: dict[str, Any] = {
        "tipo_de_comprobante": _infer_document_type_from_series(series),
        "serie": series,
        "numero": number,
        "fecha_de_emision": _normalize_import_date(
            _xml_get_nested_text(root, ["IssueDate"])
        ),
        "cliente_tipo_de_documento": (
            cstr(customer_id_node.get("schemeID")).strip()
            if customer_id_node is not None
            else ""
        ),
        "cliente_numero_de_documento": (
            cstr(customer_id_node.text).strip()
            if customer_id_node is not None and customer_id_node.text
            else ""
        ),
        "cliente_denominacion": _xml_get_nested_text(
            root,
            ["DeliveryCustomerParty", "Party", "PartyLegalEntity", "RegistrationName"],
        ),
        "cliente_direccion": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"],
        ),
        "ubigeo_origen": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "Despatch", "DespatchAddress", "ID"],
        ),
        "direccion_origen": _xml_get_nested_text(
            root,
            [
                "Shipment",
                "Delivery",
                "Despatch",
                "DespatchAddress",
                "AddressLine",
                "Line",
            ],
        ),
        "ubigeo_destino": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "DeliveryAddress", "ID"],
        ),
        "direccion_destino": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"],
        ),
        "observaciones": _clean_import_note(_xml_get_nested_text(root, ["Note"])),
        "items": _parse_items(root),
    }

    return payload


def _parse_items(root: ET.Element) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for line in _xml_findall(root, "DespatchLine"):
        delivered_quantity = _xml_get_nested_node(line, ["DeliveredQuantity"])
        item_node = _xml_get_nested_node(line, ["Item"])
        items.append(
            {
                "unidad_de_medida": (
                    cstr(delivered_quantity.get("unitCode")).strip()
                    if delivered_quantity is not None
                    and delivered_quantity.get("unitCode")
                    else "NIU"
                ),
                "codigo": _xml_get_nested_text(
                    item_node,
                    ["SellersItemIdentification", "ID"],
                ),
                "descripcion": _xml_get_nested_text(item_node, ["Description"]),
                "cantidad": (
                    cstr(delivered_quantity.text).strip()
                    if delivered_quantity is not None and delivered_quantity.text
                    else ""
                ),
            }
        )

    return items


def _xml_findall(node: ET.Element | None, local_name: str) -> list[ET.Element]:
    if node is None:
        return []

    return [child for child in node.iter() if _xml_local_name(child.tag) == local_name]


def _xml_get_nested_node(node: ET.Element | None, path: list[str]) -> ET.Element | None:
    current = node

    for local_name in path:
        if current is None:
            return None
        current = _xml_first_child(current, local_name)

    return current


def _xml_get_nested_text(node: ET.Element | None, path: list[str]) -> str:
    found = _xml_get_nested_node(node, path)
    if found is None or not found.text:
        return ""
    return cstr(found.text).strip()


def _xml_first_child(node: ET.Element, local_name: str) -> ET.Element | None:
    for child in list(node):
        if _xml_local_name(child.tag) == local_name:
            return child
    return None


def _xml_local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _split_series_number(value: Any) -> tuple[str, str]:
    text = cstr(value or "").strip()
    if not text or "-" not in text:
        return text, ""

    series, *rest = text.split("-")
    return series, "-".join(rest)


def _infer_document_type_from_series(series: Any) -> str:
    normalized = cstr(series or "").strip().upper()
    if normalized.startswith("F"):
        return "1"
    if normalized.startswith("B"):
        return "2"
    return ""


def _normalize_import_date(value: Any) -> str:
    text = cstr(value or "").strip()
    if not text:
        return ""

    if len(text) == 10 and text[2] == "-" and text[5] == "-":
        day, month, year = text.split("-")
        return f"{year}-{month}-{day}"

    return text


def _clean_import_note(value: Any) -> str:
    text = cstr(value or "").strip()
    if text.lower().startswith("obs:"):
        return text[4:].strip()
    return text
