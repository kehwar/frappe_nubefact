# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from __future__ import annotations

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import import (
	crear_guia_de_remision_desde_json,
	parse_import_json_payload,
)


class TestNubefactGuiaDeRemisionImport(FrappeTestCase):
	def test_json_import_preserves_all_supported_fields_and_raw_extensions(self):
		payload = {
			"operacion": "generar_guia",
			"tipo_de_comprobante": 8,
			"serie": "VVV1",
			"numero": 25,
			"fecha_de_emision": "01-06-2026",
			"fecha_de_inicio_de_traslado": "02-06-2026",
			"fecha_de_entrega_al_transportista": "03-06-2026",
			"cliente_tipo_de_documento": "6",
			"cliente_numero_de_documento": "20600695771",
			"cliente_denominacion": "REMITENTE",
			"cliente_direccion": "DIRECCION",
			"destinatario_documento_tipo": "1",
			"destinatario_documento_numero": "12345678",
			"destinatario_denominacion": "DESTINATARIO",
			"peso_bruto_total": "1",
			"peso_bruto_unidad_de_medida": "KGM",
			"transportista_placa_numero": "ABC123",
			"tuc_vehiculo_principal": "ABC1234567",
			"conductor_documento_tipo": "1",
			"conductor_documento_numero": "12345678",
			"conductor_denominacion": "JUAN PEREZ",
			"conductor_nombre": "JUAN",
			"conductor_apellidos": "PEREZ",
			"conductor_numero_licencia": "Q12345678",
			"mtc": "MTC123",
			"sunat_envio_indicador": "02",
			"subcontratador_documento_tipo": "6",
			"subcontratador_documento_numero": "20600695771",
			"subcontratador_denominacion": "SUBCONTRATADOR",
			"pagador_servicio_documento_tipo_identidad": "6",
			"pagador_servicio_documento_numero_identidad": "20600695771",
			"pagador_servicio_denominacion": "PAGADOR",
			"punto_de_partida_ubigeo": "150101",
			"punto_de_partida_direccion": "ORIGEN",
			"punto_de_llegada_ubigeo": "150102",
			"punto_de_llegada_direccion": "DESTINO",
			"extension_cabecera": "valor",
			"items": [
				{
					"unidad_de_medida": "NIU",
					"codigo": "ITEM-1",
					"descripcion": "ITEM",
					"cantidad": "1",
					"extension_item": "valor-item",
				}
			],
			"vehiculos_secundarios": [
				{"placa_numero": "ABC124", "tuc": "ABC1234568", "extension_vehiculo": 1}
			],
			"conductores_secundarios": [
				{
					"documento_tipo": "A",
					"documento_numero": "ABC123",
					"nombre": "ANA",
					"apellidos": "PEREZ",
					"numero_licencia": "Q12345679",
					"extension_conductor": True,
				}
			],
		}

		name = crear_guia_de_remision_desde_json(json.dumps(payload))
		doc = frappe.get_doc("Nubefact Guia De Remision", name)

		self.assertEqual(str(doc.fecha_de_entrega_al_transportista), "2026-06-03")
		self.assertEqual(doc.tuc_vehiculo_principal, "ABC1234567")
		self.assertEqual(doc.conductor_denominacion, "JUAN PEREZ")
		self.assertEqual(doc.mtc, "MTC123")
		self.assertEqual(doc.sunat_envio_indicador, "02")
		self.assertEqual(doc.subcontratador_denominacion, "SUBCONTRATADOR")
		self.assertEqual(doc.pagador_servicio_denominacion, "PAGADOR")
		self.assertEqual(json.loads(doc.custom)["extension_cabecera"], "valor")
		self.assertEqual(json.loads(doc.items[0].custom)["extension_item"], "valor-item")
		self.assertEqual(json.loads(doc.vehiculos_secundarios[0].custom)["extension_vehiculo"], 1)
		self.assertTrue(json.loads(doc.conductores_secundarios[0].custom)["extension_conductor"])

	def test_json_import_rejects_invalid_operation_or_document_type(self):
		invalid_payloads = [
			{"tipo_de_comprobante": 7},
			{"operacion": "consultar_guia", "tipo_de_comprobante": 7},
			{"operacion": "generar_guia", "tipo_de_comprobante": 1},
		]

		for payload in invalid_payloads:
			with self.subTest(payload=payload):
				with self.assertRaises(frappe.ValidationError):
					parse_import_json_payload(json.dumps(payload))

	def test_json_import_rejects_invalid_json_and_non_objects(self):
		for payload in ("not-json", "[]", '"text"'):
			with self.subTest(payload=payload):
				with self.assertRaises(frappe.ValidationError):
					parse_import_json_payload(payload)
