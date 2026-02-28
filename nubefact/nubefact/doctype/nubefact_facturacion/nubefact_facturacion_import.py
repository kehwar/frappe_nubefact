from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_import_xml import (
    parse_import_cpe_xml_payload,
)


@frappe.whitelist()
def create_invoice_from_import_file(file_name: str) -> str:
    file_doc = frappe.get_doc("File", file_name)
    content = file_doc.get_content()
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else cstr(content)

    source_name = cstr(file_doc.file_name or file_doc.file_url or "").lower()
    imported_from_xml = False
    if source_name.endswith(".json"):
        payload = parse_import_json_payload(text)
    elif source_name.endswith(".xml"):
        payload = parse_import_cpe_xml_payload(text)
        imported_from_xml = True
    else:
        frappe.throw(
            "Tipo de archivo no soportado. Solo se permiten archivos JSON y XML."
        )

    doc = frappe.new_doc("Nubefact Facturacion")
    if imported_from_xml:
        doc.set("skip_field_validation", 1)
    apply_import_payload_to_doc(doc, payload)
    doc.flags.ignore_validate = True
    doc.insert()
    return doc.name


@frappe.whitelist()
def create_invoice_from_import_json_text(json_payload: str) -> str:
    payload = parse_import_json_payload(cstr(json_payload or ""))

    doc = frappe.new_doc("Nubefact Facturacion")
    apply_import_payload_to_doc(doc, payload)
    doc.flags.ignore_validate = True
    doc.insert()
    return doc.name


def apply_import_payload_to_doc(doc: Document, payload: dict[str, Any]):
    scalar_fields = [
        "operacion",
        "tipo_de_comprobante",
        "serie",
        "numero",
        "sunat_transaction",
        "cliente_tipo_de_documento",
        "cliente_numero_de_documento",
        "cliente_denominacion",
        "cliente_direccion",
        "cliente_email",
        "cliente_email_1",
        "cliente_email_2",
        "moneda",
        "tipo_de_cambio",
        "porcentaje_de_igv",
        "descuento_global",
        "total_descuento",
        "total_anticipo",
        "total_gravada",
        "total_inafecta",
        "total_exonerada",
        "total_igv",
        "total_gratuita",
        "total_otros_cargos",
        "total_isc",
        "total_impuestos_bolsas",
        "total",
        "percepcion_tipo",
        "percepcion_base_imponible",
        "total_percepcion",
        "total_incluido_percepcion",
        "retencion_tipo",
        "retencion_base_imponible",
        "total_retencion",
        "documento_que_se_modifica_tipo",
        "documento_que_se_modifica_serie",
        "documento_que_se_modifica_numero",
        "tipo_de_nota_de_credito",
        "tipo_de_nota_de_debito",
        "detraccion_tipo",
        "detraccion_total",
        "detraccion_porcentaje",
        "medio_de_pago_detraccion",
        "ubigeo_origen",
        "direccion_origen",
        "ubigeo_destino",
        "direccion_destino",
        "detalle_viaje",
        "val_ref_serv_trans",
        "val_ref_carga_efec",
        "val_ref_carga_util",
        "punto_origen_viaje",
        "punto_destino_viaje",
        "descripcion_tramo",
        "val_ref_carga_efec_tramo_virtual",
        "configuracion_vehicular",
        "carga_util_tonel_metricas",
        "carga_efec_tonel_metricas",
        "val_ref_tonel_metrica",
        "val_pre_ref_carga_util_nominal",
        "matricula_emb_pesquera",
        "nombre_emb_pesquera",
        "descripcion_tipo_especie_vendida",
        "lugar_de_descarga",
        "cantidad_especie_vendida",
        "codigo_unico",
        "formato_de_pdf",
        "condiciones_de_pago",
        "nubecont_tipo_de_venta_codigo",
        "medio_de_pago",
        "orden_compra_servicio",
        "placa_vehiculo",
        "observaciones",
    ]

    for fieldname in scalar_fields:
        value = payload.get(fieldname)
        if value is not None:
            doc.set(fieldname, value)

    if payload.get("fecha_de_emision"):
        doc.set(
            "fecha_de_emision",
            _normalize_import_date(cstr(payload.get("fecha_de_emision"))),
        )

    if payload.get("fecha_de_vencimiento"):
        doc.set(
            "fecha_de_vencimiento",
            _normalize_import_date(cstr(payload.get("fecha_de_vencimiento"))),
        )

    if payload.get("fecha_de_descarga"):
        doc.set(
            "fecha_de_descarga",
            _normalize_import_date(cstr(payload.get("fecha_de_descarga"))),
        )

    if "enviar_automaticamente_a_la_sunat" in payload:
        doc.set(
            "enviar_automaticamente_a_la_sunat",
            1 if _to_bool(payload.get("enviar_automaticamente_a_la_sunat")) else 0,
        )

    if "enviar_automaticamente_al_cliente" in payload:
        doc.set(
            "enviar_automaticamente_al_cliente",
            1 if _to_bool(payload.get("enviar_automaticamente_al_cliente")) else 0,
        )

    if "detraccion" in payload:
        doc.set("detraccion", 1 if _to_bool(payload.get("detraccion")) else 0)

    if "generado_por_contingencia" in payload:
        doc.set(
            "generado_por_contingencia",
            1 if _to_bool(payload.get("generado_por_contingencia")) else 0,
        )

    if "bienes_region_selva" in payload:
        doc.set(
            "bienes_region_selva",
            1 if _to_bool(payload.get("bienes_region_selva")) else 0,
        )

    if "servicios_region_selva" in payload:
        doc.set(
            "servicios_region_selva",
            1 if _to_bool(payload.get("servicios_region_selva")) else 0,
        )

    if "indicador_aplicacion_retorno_vacio" in payload:
        doc.set(
            "indicador_aplicacion_retorno_vacio",
            1 if _to_bool(payload.get("indicador_aplicacion_retorno_vacio")) else 0,
        )

    doc.set("items", [])
    for row in payload.get("items") or []:
        doc.append(
            "items",
            {
                "unidad_de_medida": row.get("unidad_de_medida"),
                "codigo": row.get("codigo"),
                "codigo_producto_sunat": row.get("codigo_producto_sunat"),
                "descripcion": row.get("descripcion"),
                "cantidad": row.get("cantidad"),
                "valor_unitario": row.get("valor_unitario"),
                "precio_unitario": row.get("precio_unitario"),
                "descuento": row.get("descuento"),
                "subtotal": row.get("subtotal"),
                "tipo_de_igv": row.get("tipo_de_igv"),
                "tipo_de_ivap": row.get("tipo_de_ivap"),
                "igv": row.get("igv"),
                "impuesto_bolsas": row.get("impuesto_bolsas"),
                "total": row.get("total"),
                "anticipo_regularizacion": (
                    1 if _to_bool(row.get("anticipo_regularizacion")) else 0
                ),
                "anticipo_documento_serie": row.get("anticipo_documento_serie"),
                "anticipo_documento_numero": row.get("anticipo_documento_numero"),
                "tipo_de_isc": row.get("tipo_de_isc"),
                "isc": row.get("isc"),
            },
        )

    doc.set("guias", [])
    for row in payload.get("guias") or []:
        doc.append(
            "guias",
            {
                "guia_tipo": row.get("guia_tipo"),
                "guia_serie_numero": row.get("guia_serie_numero"),
            },
        )

    doc.set("venta_al_credito", [])
    for row in payload.get("venta_al_credito") or []:
        doc.append(
            "venta_al_credito",
            {
                "cuota": row.get("cuota"),
                "fecha_de_pago": _normalize_import_date(
                    cstr(row.get("fecha_de_pago") or "")
                ),
                "importe": row.get("importe"),
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
