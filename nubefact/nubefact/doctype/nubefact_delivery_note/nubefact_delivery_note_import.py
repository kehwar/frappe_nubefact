from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note_import_xml import (
    parse_import_despatch_xml_payload,
)


@frappe.whitelist()
def create_delivery_note_from_import_file(file_name: str) -> str:
    file_doc = frappe.get_doc("File", file_name)
    content = file_doc.get_content()
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else cstr(content)

    source_name = cstr(file_doc.file_name or file_doc.file_url or "").lower()
    if source_name.endswith(".json"):
        payload = parse_import_json_payload(text)
    elif source_name.endswith(".xml"):
        payload = parse_import_despatch_xml_payload(text)
    else:
        frappe.throw("Unsupported file type. Only JSON and XML files are allowed.")

    doc = frappe.new_doc("Nubefact Delivery Note")
    apply_import_payload_to_doc(doc, payload)
    doc.insert()
    return doc.name


@frappe.whitelist()
def create_delivery_note_from_import_json_text(json_payload: str) -> str:
    payload = parse_import_json_payload(cstr(json_payload or ""))

    doc = frappe.new_doc("Nubefact Delivery Note")
    apply_import_payload_to_doc(doc, payload)
    doc.insert()
    return doc.name


def apply_import_payload_to_doc(doc: Document, payload: dict[str, Any]):
    scalar_map = {
        "tipo_de_comprobante": "document_type",
        "serie": "series",
        "cliente_tipo_de_documento": "client_document_type",
        "cliente_numero_de_documento": "client_document_number",
        "cliente_denominacion": "client_name",
        "cliente_direccion": "client_address",
        "cliente_email": "client_email",
        "cliente_email_1": "client_email_1",
        "cliente_email_2": "client_email_2",
        "destinatario_documento_tipo": "recipient_document_type",
        "destinatario_documento_numero": "recipient_document_number",
        "destinatario_denominacion": "recipient_name",
        "motivo_de_traslado": "transfer_reason",
        "tipo_de_transporte": "transport_type",
        "peso_bruto_total": "gross_total_weight",
        "peso_bruto_unidad_de_medida": "weight_unit",
        "numero_de_bultos": "number_of_packages",
        "transportista_documento_tipo": "carrier_document_type",
        "transportista_documento_numero": "carrier_document_number",
        "transportista_denominacion": "carrier_name",
        "transportista_placa_numero": "vehicle_license_plate",
        "conductor_documento_tipo": "driver_document_type",
        "conductor_documento_numero": "driver_document_number",
        "conductor_nombre": "driver_first_name",
        "conductor_apellidos": "driver_last_name",
        "conductor_numero_licencia": "driver_license_number",
        "punto_de_partida_ubigeo": "origin_ubigeo",
        "punto_de_partida_direccion": "origin_address",
        "punto_de_partida_codigo_establecimiento_sunat": "origin_sunat_code",
        "punto_de_llegada_ubigeo": "destination_ubigeo",
        "punto_de_llegada_direccion": "destination_address",
        "punto_de_llegada_codigo_establecimiento_sunat": "destination_sunat_code",
        "formato_de_pdf": "pdf_format",
        "observaciones": "observations",
    }

    for source_key, target_field in scalar_map.items():
        value = payload.get(source_key)
        if value is not None:
            doc.set(target_field, value)

    if "numero" in payload:
        doc.set("number", payload.get("numero"))

    if payload.get("fecha_de_emision"):
        doc.set(
            "issue_date", _normalize_import_date(cstr(payload.get("fecha_de_emision")))
        )

    if payload.get("fecha_de_inicio_de_traslado"):
        doc.set(
            "transfer_start_date",
            _normalize_import_date(cstr(payload.get("fecha_de_inicio_de_traslado"))),
        )

    if "enviar_automaticamente_al_cliente" in payload:
        doc.set(
            "auto_send_to_client",
            1 if _to_bool(payload.get("enviar_automaticamente_al_cliente")) else 0,
        )

    doc.set("items", [])
    for row in payload.get("items") or []:
        doc.append(
            "items",
            {
                "unit_of_measure": row.get("unidad_de_medida"),
                "item_code": row.get("codigo"),
                "description": row.get("descripcion"),
                "quantity": row.get("cantidad"),
            },
        )

    doc.set("related_documents", [])
    for row in payload.get("documento_relacionado") or []:
        doc.append(
            "related_documents",
            {
                "document_type": row.get("tipo"),
                "series": row.get("serie"),
                "number": row.get("numero"),
            },
        )

    doc.set("secondary_vehicles", [])
    for row in payload.get("vehiculos_secundarios") or []:
        doc.append(
            "secondary_vehicles",
            {
                "license_plate": row.get("placa_numero"),
                "tuc": row.get("tuc"),
            },
        )

    doc.set("secondary_drivers", [])
    for row in payload.get("conductores_secundarios") or []:
        doc.append(
            "secondary_drivers",
            {
                "document_type": row.get("documento_tipo"),
                "document_number": row.get("documento_numero"),
                "first_name": row.get("nombre"),
                "last_name": row.get("apellidos"),
                "license_number": row.get("numero_licencia"),
            },
        )


def parse_import_json_payload(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        frappe.throw("Invalid JSON format.")

    if not isinstance(payload, dict):
        frappe.throw("JSON payload must be an object.")

    return payload


def _normalize_import_date(value: Any) -> str:
    text = cstr(value or "").strip()
    if not text:
        return ""

    if len(text) == 10 and text[2] == "-" and text[5] == "-":
        day, month, year = text.split("-")
        return f"{year}-{month}-{day}"

    return text


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y"}

    return bool(value)
