# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe.utils import cstr

MASTER_DATA = {
	"Nubefact Tipo de Comprobante": (
		{
			"codigo": "1",
			"descripcion": "Factura",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
		},
		{
			"codigo": "2",
			"descripcion": "Boleta de venta",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
		},
		{
			"codigo": "3",
			"descripcion": "Nota de crédito",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
		},
		{
			"codigo": "4",
			"descripcion": "Nota de débito",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
		},
		{
			"codigo": "7",
			"descripcion": "Guía de remisión remitente",
			"aplica_facturacion": 0,
			"aplica_guia_de_remision": 1,
		},
		{
			"codigo": "8",
			"descripcion": "Guía de remisión transportista",
			"aplica_facturacion": 0,
			"aplica_guia_de_remision": 1,
		},
	),
	"Nubefact Motivo de Traslado": (
		{"codigo": "01", "descripcion": "Venta"},
		{"codigo": "02", "descripcion": "Compra"},
		{"codigo": "03", "descripcion": "Venta con entrega a terceros"},
		{"codigo": "04", "descripcion": "Traslado entre establecimientos de la misma empresa"},
		{"codigo": "05", "descripcion": "Consignación"},
		{"codigo": "06", "descripcion": "Devolución"},
		{"codigo": "07", "descripcion": "Recojo de bienes transformados"},
		{"codigo": "08", "descripcion": "Importación"},
		{"codigo": "09", "descripcion": "Exportación"},
		{"codigo": "13", "descripcion": "Otros"},
		{"codigo": "14", "descripcion": "Venta sujeta a confirmación del comprador"},
		{"codigo": "17", "descripcion": "Traslado de bienes para transformación"},
		{"codigo": "18", "descripcion": "Traslado emisor itinerante de comprobantes de pago"},
	),
	"Nubefact Tipo de Transporte": (
		{"codigo": "01", "descripcion": "Transporte público"},
		{"codigo": "02", "descripcion": "Transporte privado"},
	),
	"Nubefact Unidad de Medida": (
		{
			"codigo": "KGM",
			"codigo_importacion_exportacion": "KG",
			"descripcion": "Kilogramo",
			"aplica_peso_bruto": 1,
		},
		{
			"codigo": "TNE",
			"codigo_importacion_exportacion": "TM",
			"descripcion": "Tonelada",
			"aplica_peso_bruto": 1,
		},
		{
			"codigo": "NIU",
			"codigo_importacion_exportacion": "U",
			"descripcion": "Unidad",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "PR",
			"codigo_importacion_exportacion": "2U",
			"descripcion": "Par",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "KT",
			"codigo_importacion_exportacion": "KIT",
			"descripcion": "Kit",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "MTR",
			"codigo_importacion_exportacion": "M",
			"descripcion": "Metro",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "PK",
			"codigo_importacion_exportacion": "PAQ",
			"descripcion": "Paquete",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "BX",
			"codigo_importacion_exportacion": "CAJ",
			"descripcion": "Caja",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "PF",
			"codigo_importacion_exportacion": "PAL",
			"descripcion": "Paleta",
			"aplica_peso_bruto": 0,
		},
		{
			"codigo": "SET",
			"codigo_importacion_exportacion": "SET",
			"descripcion": "Set",
			"aplica_peso_bruto": 0,
		},
		{"codigo": "ZZ", "descripcion": "Unidad de servicio", "aplica_peso_bruto": 0},
	),
	"Nubefact Tipo de Documento": (
		{
			"codigo": "6",
			"descripcion": "RUC - Registro Único de Contribuyentes",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 0,
			"aplica_transportista": 1,
		},
		{
			"codigo": "1",
			"descripcion": "DNI - Documento Nacional de Identidad",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 1,
			"aplica_transportista": 0,
		},
		{
			"codigo": "-",
			"descripcion": "Varios - Ventas menores y otros",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
			"aplica_conductor": 0,
			"aplica_transportista": 0,
		},
		{
			"codigo": "4",
			"descripcion": "Carnet de extranjería",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 1,
			"aplica_transportista": 0,
		},
		{
			"codigo": "7",
			"descripcion": "Pasaporte",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 1,
			"aplica_transportista": 0,
		},
		{
			"codigo": "A",
			"descripcion": "Cédula diplomática de identidad",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 1,
			"aplica_transportista": 0,
		},
		{
			"codigo": "B",
			"descripcion": "Documento de identidad del país de residencia - No domiciliado",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
			"aplica_conductor": 0,
			"aplica_transportista": 0,
		},
		{
			"codigo": "0",
			"descripcion": "No domiciliado, sin RUC (exportación)",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 1,
			"aplica_conductor": 1,
			"aplica_transportista": 0,
		},
		{
			"codigo": "G",
			"descripcion": "Salvoconducto",
			"aplica_facturacion": 1,
			"aplica_guia_de_remision": 0,
			"aplica_conductor": 0,
			"aplica_transportista": 0,
		},
	),
	"Nubefact Tipo de Documento Relacionado": (
		{"codigo": "01", "descripcion": "Factura"},
		{"codigo": "03", "descripcion": "Boleta de venta"},
		{"codigo": "09", "descripcion": "Guía de remisión remitente"},
		{"codigo": "31", "descripcion": "Guía de remisión transportista"},
	),
	"Nubefact Indicador Sunat": (
		{
			"codigo": "01",
			"descripcion": "Pagador del flete: remitente",
			"aplica_gre_remitente": 0,
			"aplica_gre_transportista": 1,
		},
		{
			"codigo": "02",
			"descripcion": "Pagador del flete: subcontratador",
			"aplica_gre_remitente": 0,
			"aplica_gre_transportista": 1,
		},
		{
			"codigo": "03",
			"descripcion": "Pagador del flete: tercero",
			"aplica_gre_remitente": 0,
			"aplica_gre_transportista": 1,
		},
		{
			"codigo": "04",
			"descripcion": "Retorno de vehículo con envases vacíos",
			"aplica_gre_remitente": 1,
			"aplica_gre_transportista": 1,
		},
		{
			"codigo": "05",
			"descripcion": "Retorno de vehículo vacío",
			"aplica_gre_remitente": 1,
			"aplica_gre_transportista": 1,
		},
		{
			"codigo": "06",
			"descripcion": "Traslado en vehículo M1 o L / Transporte subcontratado",
			"aplica_gre_remitente": 1,
			"aplica_gre_transportista": 0,
		},
		{
			"codigo": "07",
			"descripcion": "Vehículo y conductores del transportista",
			"aplica_gre_remitente": 1,
			"aplica_gre_transportista": 0,
		},
	),
	"Nubefact Codigo de Documento Relacionado": (
		{"codigo": "50", "descripcion": "Declaración Aduanera de Mercancías (DAM)"},
		{"codigo": "52", "descripcion": "Declaración Simplificada (DS)"},
	),
}

ITEM_DOCTYPES_WITH_UNITS = (
	"Nubefact Facturacion Item",
	"Nubefact Guia De Remision Item",
)


def load_master_data() -> int:
	"""Reconcile bundled code catalogs and preserve units already used by documents."""
	created = 0
	for doctype, records in MASTER_DATA.items():
		created += _upsert_records(doctype, records)
	created += _load_existing_units()
	return created


def _upsert_records(doctype: str, records: Iterable[dict]) -> int:
	created = 0
	for record in records:
		code = record["codigo"]
		if not frappe.db.exists(doctype, code):
			frappe.get_doc({"doctype": doctype, **record}).insert(ignore_permissions=True)
			created += 1
			continue

		current = frappe.get_doc(doctype, code)
		changed = False
		for fieldname, value in record.items():
			if current.get(fieldname) != value:
				current.set(fieldname, value)
				changed = True
		if changed:
			current.save(ignore_permissions=True)
	return created


def _load_existing_units() -> int:
	created = 0
	for doctype in ITEM_DOCTYPES_WITH_UNITS:
		for row in frappe.get_all(
			doctype,
			filters={"unidad_de_medida": ["is", "set"]},
			fields=["name", "unidad_de_medida"],
		):
			original_code = cstr(row.unidad_de_medida)
			code = original_code.strip()
			if code != original_code:
				frappe.db.set_value(doctype, row.name, "unidad_de_medida", code, update_modified=False)
			if not code or frappe.db.exists("Nubefact Unidad de Medida", code):
				continue
			frappe.get_doc(
				{
					"doctype": "Nubefact Unidad de Medida",
					"codigo": code,
					"descripcion": "Unidad de medida existente",
					"aplica_peso_bruto": 0,
				}
			).insert(ignore_permissions=True)
			created += 1
	return created
