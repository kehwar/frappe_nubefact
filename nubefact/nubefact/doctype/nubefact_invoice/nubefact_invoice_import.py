from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cstr


@frappe.whitelist()
def create_invoice_from_import_file(file_name: str) -> str:
    file_doc = frappe.get_doc("File", file_name)
    content = file_doc.get_content()
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else cstr(content)

    source_name = cstr(file_doc.file_name or file_doc.file_url or "").lower()
    if source_name.endswith(".json"):
        payload = parse_import_json_payload(text)
    else:
        frappe.throw("Unsupported file type. Only JSON files are allowed.")

    doc = frappe.new_doc("Nubefact Invoice")
    apply_import_payload_to_doc(doc, payload)
    doc.insert()
    return doc.name


@frappe.whitelist()
def create_invoice_from_import_json_text(json_payload: str) -> str:
    payload = parse_import_json_payload(cstr(json_payload or ""))

    doc = frappe.new_doc("Nubefact Invoice")
    apply_import_payload_to_doc(doc, payload)
    doc.insert()
    return doc.name


def apply_import_payload_to_doc(doc: Document, payload: dict[str, Any]):
    scalar_map = {
        "tipo_de_comprobante": "document_type",
        "serie": "series",
        "tipo_de_operacion": "sunat_transaction",
        "cliente_tipo_de_documento": "client_document_type",
        "cliente_numero_de_documento": "client_document_number",
        "cliente_denominacion": "client_name",
        "cliente_direccion": "client_address",
        "cliente_email": "client_email",
        "cliente_email_1": "client_email_1",
        "cliente_email_2": "client_email_2",
        "moneda": "currency",
        "porcentaje_de_igv": "igv_percentage",
        "total_gravada": "total_taxable",
        "total_inafecta": "total_unaffected",
        "total_exonerada": "total_exempt",
        "total_igv": "total_igv",
        "descuento_global": "global_discount",
        "total_descuento": "total_discount",
        "total_anticipo": "total_advance",
        "total_gratuita": "total_free",
        "total_otros_cargos": "total_other_charges",
        "total": "total",
        "tipo_de_cambio": "exchange_rate",
        "percepcion_tipo": "perception_type",
        "percepcion_base_imponible": "perception_base",
        "total_percepcion": "total_perception",
        "total_incluido_percepcion": "total_with_perception",
        "retencion_tipo": "retention_type",
        "retencion_base_imponible": "retention_base",
        "total_retencion": "total_retention",
        "impuesto_bolsa_plastica": "total_plastic_bag_tax",
        "tipo_de_comprobante_modificado": "modifies_document_type",
        "serie_comprobante_modificado": "modifies_series",
        "numero_comprobante_modificado": "modifies_number",
        "tipo_de_nota_de_credito": "credit_note_reason",
        "tipo_de_nota_de_debito": "debit_note_reason",
        "condiciones_de_pago": "payment_terms",
        "medio_de_pago": "payment_method",
        "placa_vehiculo": "vehicle_license_plate",
        "orden_compra_servicio": "purchase_order",
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

    if payload.get("fecha_de_vencimiento"):
        doc.set(
            "due_date",
            _normalize_import_date(cstr(payload.get("fecha_de_vencimiento"))),
        )

    if "enviar_automaticamente_a_la_sunat" in payload:
        doc.set(
            "auto_send_to_sunat",
            1 if _to_bool(payload.get("enviar_automaticamente_a_la_sunat")) else 0,
        )

    if "enviar_automaticamente_al_cliente" in payload:
        doc.set(
            "auto_send_to_client",
            1 if _to_bool(payload.get("enviar_automaticamente_al_cliente")) else 0,
        )

    if "detraccion" in payload:
        doc.set(
            "subject_to_detraction", 1 if _to_bool(payload.get("detraccion")) else 0
        )

    if "generado_por_contingencia" in payload:
        doc.set(
            "generated_by_contingency",
            1 if _to_bool(payload.get("generado_por_contingencia")) else 0,
        )

    if "bienes_region_selva" in payload:
        doc.set(
            "goods_from_jungle",
            1 if _to_bool(payload.get("bienes_region_selva")) else 0,
        )

    if "servicios_region_selva" in payload:
        doc.set(
            "services_from_jungle",
            1 if _to_bool(payload.get("servicios_region_selva")) else 0,
        )

    doc.set("items", [])
    for row in payload.get("items") or []:
        doc.append(
            "items",
            {
                "unit_of_measure": row.get("unidad_de_medida"),
                "item_code": row.get("codigo"),
                "sunat_product_code": row.get("codigo_producto_sunat"),
                "description": row.get("descripcion"),
                "quantity": row.get("cantidad"),
                "unit_value": row.get("valor_unitario"),
                "unit_price": row.get("precio_unitario"),
                "discount": row.get("descuento"),
                "subtotal": row.get("subtotal"),
                "igv_type": row.get("tipo_de_igv"),
                "igv": row.get("igv"),
                "total": row.get("total"),
                "advance_regularization": (
                    1 if _to_bool(row.get("anticipo_regularizacion")) else 0
                ),
                "advance_document_series": row.get("anticipo_documento_serie"),
                "advance_document_number": row.get("anticipo_documento_numero"),
            },
        )

    doc.set("delivery_guides", [])
    for row in payload.get("guias") or []:
        doc.append(
            "delivery_guides",
            {
                "guide_type": row.get("guia_tipo"),
                "guide_series_number": row.get("guia_serie_numero"),
            },
        )

    doc.set("credit_installments", [])
    for row in payload.get("venta_al_credito") or []:
        doc.append(
            "credit_installments",
            {
                "installment_number": row.get("cuota"),
                "payment_date": _normalize_import_date(
                    cstr(row.get("fecha_de_pago") or "")
                ),
                "amount": row.get("importe"),
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
