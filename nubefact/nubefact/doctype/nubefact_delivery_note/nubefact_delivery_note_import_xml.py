from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import frappe
from frappe.utils import cstr


def parse_import_despatch_xml_payload(text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        frappe.throw("Invalid XML format.")

    root_name = _xml_local_name(root.tag)
    if root_name == "ApplicationResponse":
        frappe.throw(
            "CDR XML cannot be used to create a Delivery Note. Use DespatchAdvice XML."
        )
    if root_name != "DespatchAdvice":
        frappe.throw("Unsupported XML type. Expected SUNAT DespatchAdvice XML.")

    full_number = _xml_get_nested_text(root, ["ID"])
    series, number = _split_series_number(full_number)
    document_type = _infer_document_type_from_series(series)

    customer_id_node = _xml_get_nested_node(
        root,
        ["DeliveryCustomerParty", "Party", "PartyIdentification", "ID"],
    )
    gross_weight_node = _xml_get_nested_node(root, ["Shipment", "GrossWeightMeasure"])

    payload: dict[str, Any] = {
        "tipo_de_comprobante": document_type,
        "serie": series,
        "numero": number,
        "fecha_de_emision": _normalize_import_date(
            _xml_get_nested_text(root, ["IssueDate"])
        ),
        "fecha_de_inicio_de_traslado": _normalize_import_date(
            _xml_get_nested_text(
                root,
                ["Shipment", "ShipmentStage", "TransitPeriod", "StartDate"],
            )
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
        "motivo_de_traslado": _xml_get_nested_text(
            root,
            ["Shipment", "HandlingCode"],
        ),
        "tipo_de_transporte": _xml_get_nested_text(
            root,
            ["Shipment", "ShipmentStage", "TransportModeCode"],
        ),
        "peso_bruto_total": (
            cstr(gross_weight_node.text).strip()
            if gross_weight_node is not None and gross_weight_node.text
            else ""
        ),
        "peso_bruto_unidad_de_medida": (
            cstr(gross_weight_node.get("unitCode")).strip()
            if gross_weight_node is not None and gross_weight_node.get("unitCode")
            else ""
        ),
        "numero_de_bultos": _xml_get_nested_text(
            root,
            ["Shipment", "TotalTransportHandlingUnitQuantity"],
        )
        or "1",
        "punto_de_partida_ubigeo": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "Despatch", "DespatchAddress", "ID"],
        ),
        "punto_de_partida_direccion": _xml_get_nested_text(
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
        "punto_de_llegada_ubigeo": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "DeliveryAddress", "ID"],
        ),
        "punto_de_llegada_direccion": _xml_get_nested_text(
            root,
            ["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"],
        ),
        "observaciones": _clean_import_note(_xml_get_nested_text(root, ["Note"])),
        "transportista_documento_tipo": _xml_get_nested_attr(
            root,
            ["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"],
            "schemeID",
        ),
        "transportista_documento_numero": _xml_get_nested_text(
            root,
            ["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"],
        ),
        "transportista_denominacion": _xml_get_nested_text(
            root,
            [
                "Shipment",
                "ShipmentStage",
                "CarrierParty",
                "PartyLegalEntity",
                "RegistrationName",
            ],
        ),
        "items": _parse_import_xml_items(root),
        "documento_relacionado": _parse_import_xml_related_documents(root),
    }

    if cstr(document_type) == "8":
        payload["destinatario_documento_tipo"] = payload.get(
            "cliente_tipo_de_documento"
        )
        payload["destinatario_documento_numero"] = payload.get(
            "cliente_numero_de_documento"
        )
        payload["destinatario_denominacion"] = payload.get("cliente_denominacion")

    return payload


def _parse_import_xml_items(root: ET.Element) -> list[dict[str, Any]]:
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


def _parse_import_xml_related_documents(root: ET.Element) -> list[dict[str, Any]]:
    related_documents: list[dict[str, Any]] = []

    for reference in _xml_findall(root, "AdditionalDocumentReference"):
        full_number = _xml_get_nested_text(reference, ["ID"])
        series, number = _split_series_number(full_number)

        related_documents.append(
            {
                "tipo": _xml_get_nested_text(reference, ["DocumentTypeCode"]),
                "serie": series,
                "numero": number,
            }
        )

    return related_documents


def _xml_findall(node: ET.Element | None, local_name: str) -> list[ET.Element]:
    if node is None:
        return []

    return [child for child in node.iter() if _xml_local_name(child.tag) == local_name]


def _xml_get_nested_node(
    node: ET.Element | None,
    path: list[str],
) -> ET.Element | None:
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


def _xml_get_nested_attr(
    node: ET.Element | None, path: list[str], attr_name: str
) -> str:
    found = _xml_get_nested_node(node, path)
    if found is None:
        return ""
    return cstr(found.get(attr_name) or "").strip()


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
    if normalized.startswith("T"):
        return "7"
    if normalized.startswith("V"):
        return "8"
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
