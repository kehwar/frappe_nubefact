from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import_xml import (
    parse_import_despatch_xml_payload,
)


@frappe.whitelist()
def crear_guia_de_remision_desde_archivo(file_name: str) -> str:
    file_doc = frappe.get_doc("File", file_name)
    content = file_doc.get_content()
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else cstr(content)

    source_name = cstr(file_doc.file_name or file_doc.file_url or "").lower()
    if source_name.endswith(".json"):
        payload = parse_import_json_payload(text)
    elif source_name.endswith(".xml"):
        payload = parse_import_despatch_xml_payload(text)
    else:
        frappe.throw(
            "Tipo de archivo no soportado. Solo se permiten archivos JSON y XML."
        )

    doc = frappe.new_doc("Nubefact Guia De Remision")
    apply_import_payload_to_doc(doc, payload)
    doc.flags.ignore_validate = True
    doc.insert()
    return doc.name


@frappe.whitelist()
def crear_guia_de_remision_desde_json(json_payload: str) -> str:
    payload = parse_import_json_payload(cstr(json_payload or ""))

    doc = frappe.new_doc("Nubefact Guia De Remision")
    apply_import_payload_to_doc(doc, payload)
    doc.flags.ignore_validate = True
    doc.insert()
    return doc.name


def apply_import_payload_to_doc(doc: Document, payload: dict[str, Any]):
    scalar_map = {
        "tipo_de_comprobante": "tipo_de_comprobante",
        "serie": "serie",
        "cliente_tipo_de_documento": "cliente_tipo_de_documento",
        "cliente_numero_de_documento": "cliente_numero_de_documento",
        "cliente_denominacion": "cliente_denominacion",
        "cliente_direccion": "cliente_direccion",
        "cliente_email": "cliente_email",
        "cliente_email_1": "cliente_email_1",
        "cliente_email_2": "cliente_email_2",
        "destinatario_documento_tipo": "destinatario_documento_tipo",
        "destinatario_documento_numero": "destinatario_documento_numero",
        "destinatario_denominacion": "destinatario_denominacion",
        "motivo_de_traslado": "motivo_de_traslado",
        "tipo_de_transporte": "tipo_de_transporte",
        "peso_bruto_total": "peso_bruto_total",
        "peso_bruto_unidad_de_medida": "peso_bruto_unidad_de_medida",
        "numero_de_bultos": "numero_de_bultos",
        "transportista_documento_tipo": "transportista_documento_tipo",
        "transportista_documento_numero": "transportista_documento_numero",
        "transportista_denominacion": "transportista_denominacion",
        "transportista_placa_numero": "transportista_placa_numero",
        "conductor_documento_tipo": "conductor_documento_tipo",
        "conductor_documento_numero": "conductor_documento_numero",
        "conductor_nombre": "conductor_nombre",
        "conductor_apellidos": "conductor_apellidos",
        "conductor_numero_licencia": "conductor_numero_licencia",
        "punto_de_partida_ubigeo": "punto_de_partida_ubigeo",
        "punto_de_partida_direccion": "punto_de_partida_direccion",
        "punto_de_partida_codigo_establecimiento_sunat": "punto_de_partida_codigo_establecimiento_sunat",
        "punto_de_llegada_ubigeo": "punto_de_llegada_ubigeo",
        "punto_de_llegada_direccion": "punto_de_llegada_direccion",
        "punto_de_llegada_codigo_establecimiento_sunat": "punto_de_llegada_codigo_establecimiento_sunat",
        "formato_de_pdf": "formato_de_pdf",
        "observaciones": "observaciones",
        "documento_relacionado_codigo": "documento_relacionado_codigo",
        "motivo_de_traslado_otros_descripcion": "motivo_de_traslado_otros_descripcion",
    }

    for source_key, target_field in scalar_map.items():
        value = payload.get(source_key)
        if value is not None:
            doc.set(target_field, value)

    if "numero" in payload:
        doc.set("numero", payload.get("numero"))

    if payload.get("fecha_de_emision"):
        doc.set(
            "fecha_de_emision",
            _normalize_import_date(cstr(payload.get("fecha_de_emision"))),
        )

    if payload.get("fecha_de_inicio_de_traslado"):
        doc.set(
            "fecha_de_inicio_de_traslado",
            _normalize_import_date(cstr(payload.get("fecha_de_inicio_de_traslado"))),
        )

    if "enviar_automaticamente_al_cliente" in payload:
        doc.set(
            "enviar_automaticamente_al_cliente",
            1 if _to_bool(payload.get("enviar_automaticamente_al_cliente")) else 0,
        )

    doc.set("items", [])
    for row in payload.get("items") or []:
        doc.append(
            "items",
            {
                "unidad_de_medida": row.get("unidad_de_medida"),
                "codigo": row.get("codigo"),
                "descripcion": row.get("descripcion"),
                "cantidad": row.get("cantidad"),
                "codigo_dam": row.get("codigo_dam"),
            },
        )

    doc.set("documento_relacionado", [])
    for row in payload.get("documento_relacionado") or []:
        doc.append(
            "documento_relacionado",
            {
                "tipo": row.get("tipo"),
                "serie": row.get("serie"),
                "numero": row.get("numero"),
            },
        )

    doc.set("vehiculos_secundarios", [])
    for row in payload.get("vehiculos_secundarios") or []:
        doc.append(
            "vehiculos_secundarios",
            {
                "placa_numero": row.get("placa_numero"),
                "tuc": row.get("tuc"),
            },
        )

    doc.set("conductores_secundarios", [])
    for row in payload.get("conductores_secundarios") or []:
        doc.append(
            "conductores_secundarios",
            {
                "documento_tipo": row.get("documento_tipo"),
                "documento_numero": row.get("documento_numero"),
                "nombre": row.get("nombre"),
                "apellidos": row.get("apellidos"),
                "numero_licencia": row.get("numero_licencia"),
            },
        )


def parse_import_json_payload(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        frappe.throw("Formato JSON inválido.")

    if not isinstance(payload, dict):
        frappe.throw("El payload JSON debe ser un objeto.")

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
