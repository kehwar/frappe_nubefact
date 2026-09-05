# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate, random_string

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision import (
	enviar_a_nubefact,
	refrescar_estado_sunat,
)


def make_valid_gre(**overrides):
	values = {
		"tipo_de_comprobante": "7",
		"serie": "TTT1",
		"numero": 1,
		"fecha_de_emision": nowdate(),
		"fecha_de_inicio_de_traslado": add_days(nowdate(), 1),
		"fecha_de_entrega_al_transportista": add_days(nowdate(), 2),
		"cliente_tipo_de_documento": "6",
		"cliente_numero_de_documento": "20600695771",
		"cliente_denominacion": "CLIENTE DE PRUEBA",
		"cliente_direccion": "AV. PRUEBA 123",
		"motivo_de_traslado": "01",
		"tipo_de_transporte": "01",
		"peso_bruto_total": 1,
		"peso_bruto_unidad_de_medida": "KGM",
		"numero_de_bultos": 1,
		"transportista_documento_tipo": "6",
		"transportista_documento_numero": "20600695771",
		"transportista_denominacion": "TRANSPORTISTA DE PRUEBA",
		"transportista_placa_numero": "ABC123",
		"punto_de_partida_ubigeo": "150101",
		"punto_de_partida_direccion": "ORIGEN DE PRUEBA",
		"punto_de_llegada_ubigeo": "150102",
		"punto_de_llegada_direccion": "DESTINO DE PRUEBA",
	}
	values.update(overrides)
	if values["tipo_de_comprobante"] == "8":
		values.update(
			{
				"serie": overrides.get("serie", "VVV1"),
				"destinatario_documento_tipo": "6",
				"destinatario_documento_numero": "20600695771",
				"destinatario_denominacion": "DESTINATARIO DE PRUEBA",
				"conductor_documento_tipo": "1",
				"conductor_documento_numero": "12345678",
				"conductor_nombre": "JUAN",
				"conductor_apellidos": "PEREZ",
				"conductor_numero_licencia": "Q12345678",
			}
		)

	doc = frappe.new_doc("Nubefact Guia De Remision")
	doc.update(values)
	doc.append(
		"items",
		{
			"unidad_de_medida": "NIU",
			"codigo": "ITEM-1",
			"descripcion": "ITEM DE PRUEBA",
			"cantidad": 1,
		},
	)
	return doc


class TestNubefactGuiaDeRemision(FrappeTestCase):
	def make_local(self):
		company = frappe.get_all("Company", pluck="name", limit=1)[0]
		return frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": f"Local GRE {random_string(8)}",
				"company": company,
				"ruta_api": "https://api.example.test/gre",
				"token_api": "test-token",
				"ubigeo": "150101",
				"direccion": "ORIGEN DE PRUEBA",
				"codigo_sunat": "0000",
			}
		).insert()

	def make_series(self, local, *, numero=1):
		return frappe.get_doc(
			{
				"doctype": "Nubefact Series",
				"company": local.company,
				"local": local.name,
				"tipo_de_comprobante": "7",
				"serie": f"T{random_string(3).upper()}",
				"numero": numero,
			}
		).insert()

	@staticmethod
	def make_http_response(payload):
		response = Mock(status_code=200, ok=True, text="")
		response.json.return_value = payload
		return response

	def test_rejects_catalog_codes_outside_gre_scope(self):
		with self.assertRaises(frappe.ValidationError):
			make_valid_gre(tipo_de_comprobante="1")._validate_document_rules()

		with self.assertRaises(frappe.ValidationError):
			make_valid_gre(peso_bruto_unidad_de_medida="NIU")._validate_document_rules()

		with self.assertRaises(frappe.ValidationError):
			make_valid_gre(tipo_de_transporte="99")._validate_document_rules()

	def test_draft_can_be_saved_without_numero(self):
		doc = make_valid_gre(numero=None).insert()

		self.assertFalse(doc.numero)
		self.assertEqual(doc.title, "TTT1-")

	def test_public_remitente_requires_delivery_date(self):
		doc = make_valid_gre(fecha_de_entrega_al_transportista=None)

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_save_rejects_invalid_header_formats_and_ranges(self):
		invalid_values = [
			{"serie": "F001"},
			{"serie": "TT01X"},
			{"numero": 0},
			{"numero": 100_000_000},
			{"fecha_de_emision": add_days(nowdate(), -2)},
			{"fecha_de_inicio_de_traslado": add_days(nowdate(), -1)},
			{"fecha_de_entrega_al_transportista": add_days(nowdate(), -1)},
			{"cliente_numero_de_documento": "X" * 16},
			{"cliente_denominacion": "X" * 101},
			{"cliente_direccion": "X" * 101},
			{"cliente_email": "not-an-email"},
			{"peso_bruto_total": -1},
			{"numero_de_bultos": 1_000_000},
			{"transportista_documento_tipo": "1"},
			{"transportista_documento_numero": "12345678"},
			{"transportista_placa_numero": "ABC-123"},
			{"punto_de_partida_ubigeo": "15010"},
			{"punto_de_partida_direccion": "X" * 151},
			{"punto_de_llegada_ubigeo": "ABCDEF"},
			{"formato_de_pdf": "A5"},
			{"tuc_vehiculo_principal": "ABC1234567"},
		]

		for overrides in invalid_values:
			with self.subTest(overrides=overrides):
				with self.assertRaises(frappe.ValidationError):
					make_valid_gre(**overrides).insert()

	def test_save_enforces_conditional_requirements_and_catalogs(self):
		invalid_values = [
			{"motivo_de_traslado": "19"},
			{"motivo_de_traslado": "13", "motivo_de_traslado_otros_descripcion": None},
			{"motivo_de_traslado": "08", "documento_relacionado_codigo": None},
			{
				"motivo_de_traslado": "04",
				"punto_de_partida_codigo_establecimiento_sunat": None,
				"punto_de_llegada_codigo_establecimiento_sunat": None,
			},
			{"sunat_envio_indicador": "01"},
			{"sunat_envio_indicador": "02"},
			{"tipo_de_comprobante": "8", "sunat_envio_indicador": "03"},
		]

		for overrides in invalid_values:
			with self.subTest(overrides=overrides):
				with self.assertRaises(frappe.ValidationError):
					make_valid_gre(**overrides).insert()

	def test_save_validates_items_related_documents_and_secondary_rows(self):
		invalid_docs = []

		negative_quantity = make_valid_gre()
		negative_quantity.items[0].cantidad = -1
		invalid_docs.append(negative_quantity)

		invalid_unit = make_valid_gre()
		invalid_unit.items[0].unidad_de_medida = "n-iu"
		invalid_docs.append(invalid_unit)

		missing_dam = make_valid_gre(motivo_de_traslado="08", documento_relacionado_codigo="50")
		invalid_docs.append(missing_dam)

		invalid_related = make_valid_gre()
		invalid_related.append("documento_relacionado", {"tipo": "01", "serie": "F01", "numero": "001"})
		invalid_docs.append(invalid_related)

		incoherent_related = make_valid_gre()
		incoherent_related.append("documento_relacionado", {"tipo": "01", "serie": "B001", "numero": "1"})
		invalid_docs.append(incoherent_related)

		too_many_vehicles = make_valid_gre(tipo_de_comprobante="8")
		for plate in ("ABC124", "ABC125", "ABC126"):
			too_many_vehicles.append("vehiculos_secundarios", {"placa_numero": plate})
		invalid_docs.append(too_many_vehicles)

		too_many_drivers = make_valid_gre(tipo_de_comprobante="8")
		for number in ("12345671", "12345672", "12345673"):
			too_many_drivers.append(
				"conductores_secundarios",
				{
					"documento_tipo": "1",
					"documento_numero": number,
					"nombre": "JUAN",
					"apellidos": "PEREZ",
					"numero_licencia": "Q12345678",
				},
			)
		invalid_docs.append(too_many_drivers)

		for doc in invalid_docs:
			with self.subTest(rows=len(doc.items)):
				with self.assertRaises(frappe.ValidationError):
					doc.insert()

	def test_generate_payload_only_contains_fields_applicable_to_gre_type(self):
		public_payload = make_valid_gre()._build_generate_payload()
		self.assertEqual(
			public_payload["fecha_de_entrega_al_transportista"],
			getdate(add_days(nowdate(), 2)).strftime("%d-%m-%Y"),
		)
		self.assertNotIn("conductor_documento_tipo", public_payload)
		self.assertNotIn("tuc_vehiculo_principal", public_payload)

		private_payload = make_valid_gre(
			tipo_de_transporte="02",
			conductor_documento_tipo="A",
			conductor_documento_numero="ABC123",
			conductor_nombre="JUAN",
			conductor_apellidos="PEREZ",
			conductor_numero_licencia="Q12345678",
		)._build_generate_payload()
		self.assertNotIn("fecha_de_entrega_al_transportista", private_payload)
		self.assertNotIn("transportista_documento_tipo", private_payload)
		self.assertIn("conductor_documento_tipo", private_payload)

		carrier_payload = make_valid_gre(tipo_de_comprobante="8")._build_generate_payload()
		for fieldname in ("motivo_de_traslado", "tipo_de_transporte", "numero_de_bultos"):
			self.assertNotIn(fieldname, carrier_payload)
		self.assertNotIn("transportista_documento_tipo", carrier_payload)
		self.assertIn("destinatario_documento_tipo", carrier_payload)

	def test_valid_private_remitente_and_transportista_can_be_saved(self):
		private_doc = make_valid_gre(
			motivo_de_traslado="03",
			tipo_de_transporte="02",
			conductor_documento_tipo="A",
			conductor_documento_numero="ABC123",
			conductor_nombre="JUAN",
			conductor_apellidos="PEREZ",
			conductor_numero_licencia="Q12345678",
		)
		private_doc.insert()

		carrier_doc = make_valid_gre(
			tipo_de_comprobante="8",
			sunat_envio_indicador="03",
			pagador_servicio_documento_tipo_identidad="6",
			pagador_servicio_documento_numero_identidad="20600695771",
			pagador_servicio_denominacion="PAGADOR DE PRUEBA",
		)
		carrier_doc.insert()

		self.assertEqual(private_doc.status, "Borrador")
		self.assertEqual(carrier_doc.status, "Borrador")

	def test_link_catalogs_match_the_gre_manual(self):
		self.assertEqual(
			set(frappe.get_all("Nubefact Motivo de Traslado", pluck="name")),
			{"01", "02", "03", "04", "05", "06", "07", "08", "09", "13", "14", "17", "18"},
		)
		self.assertEqual(
			set(
				frappe.get_all(
					"Nubefact Tipo de Documento",
					filters={"aplica_transportista": 1},
					pluck="name",
				)
			),
			{"6"},
		)
		self.assertEqual(
			set(
				frappe.get_all(
					"Nubefact Tipo de Documento",
					filters={"aplica_conductor": 1},
					pluck="name",
				)
			),
			{"1", "4", "7", "A", "0"},
		)
		self.assertEqual(
			set(frappe.get_all("Nubefact Indicador Sunat", pluck="name")),
			{"01", "02", "03", "04", "05", "06", "07"},
		)

		meta = frappe.get_meta("Nubefact Guia De Remision")
		self.assertEqual(
			set(filter(None, meta.get_field("formato_de_pdf").options.splitlines())),
			{"A4", "TICKET"},
		)

	def test_skip_validation_and_raw_payload_override_remain_available(self):
		doc = make_valid_gre(serie="INVALID", skip_field_validation=1, custom={"serie": "CUSTOM"})
		doc.insert()

		self.assertEqual(doc._build_generate_payload()["serie"], "CUSTOM")

	@patch(
		"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.enqueue_nubefact_file_downloads"
	)
	@patch("nubefact.utils.nubefact.requests.post")
	def test_generate_and_query_rpc_persist_the_sunat_lifecycle(self, post, enqueue_files):
		local = self.make_local()
		series = self.make_series(local)
		doc = make_valid_gre(
			company=local.company,
			local=local.name,
			nubefact_series=series.name,
			serie=series.serie,
			numero=None,
		).insert()
		post.side_effect = [
			self.make_http_response(
				{
					"tipo_de_comprobante": 7,
					"serie": series.serie,
					"numero": 1,
					"aceptada_por_sunat": False,
				}
			),
			self.make_http_response(
				{
					"tipo_de_comprobante": 7,
					"serie": series.serie,
					"numero": 1,
					"aceptada_por_sunat": True,
					"enlace_del_pdf": "https://files.example.test/guide.pdf",
				}
			),
		]

		generated = enviar_a_nubefact(doc.name)
		self.assertEqual(generated["status"], "Pendiente de Aceptacion")
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "numero"), 1)
		self.assertEqual(frappe.db.get_value(series.doctype, series.name, "numero"), 2)
		first_request = post.call_args_list[0]
		self.assertEqual(first_request.args[0], "https://api.example.test/gre")
		self.assertEqual(first_request.kwargs["headers"]["Authorization"], "test-token")
		self.assertEqual(first_request.kwargs["json"]["operacion"], "generar_guia")
		self.assertEqual(
			first_request.kwargs["json"]["fecha_de_entrega_al_transportista"],
			getdate(add_days(nowdate(), 2)).strftime("%d-%m-%Y"),
		)
		self.assertEqual(
			enqueue_files.call_args.kwargs["request_payload"]["operacion"],
			"generar_guia",
		)
		self.assertEqual(enqueue_files.call_args.kwargs["response_payload"]["numero"], 1)

		refreshed = refrescar_estado_sunat(doc.name)
		self.assertEqual(refreshed["status"], "Aceptada")
		self.assertEqual(
			post.call_args_list[1].kwargs["json"],
			{
				"operacion": "consultar_guia",
				"tipo_de_comprobante": 7,
				"serie": series.serie,
				"numero": "1",
			},
		)
		persisted = frappe.get_doc(doc.doctype, doc.name)
		self.assertEqual(persisted.status, "Aceptada")
		self.assertIsNone(enqueue_files.call_args.kwargs["request_payload"])
		self.assertIsNone(enqueue_files.call_args.kwargs["response_payload"])
		self.assertEqual(
			frappe.db.count("Nubefact API Log", {"referencia_guia_de_remision": doc.name}),
			2,
		)

	@patch(
		"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.enqueue_nubefact_file_downloads"
	)
	@patch("nubefact.utils.nubefact.requests.post")
	def test_generate_keeps_base64_transient_except_in_api_log(self, post, enqueue_files):
		local = self.make_local()
		series = self.make_series(local)
		doc = make_valid_gre(
			company=local.company,
			local=local.name,
			nubefact_series=series.name,
			serie=series.serie,
			numero=None,
		).insert()
		post.return_value = self.make_http_response(
			{
				"numero": 1,
				"aceptada_por_sunat": True,
				"pdf_zip_base64": "PDF-BASE64",
				"xml_zip_base64": "XML-BASE64",
				"cdr_zip_base64": "CDR-BASE64",
			}
		)

		result = enviar_a_nubefact(doc.name)

		self.assertNotIn("pdf_zip_base64", result)
		self.assertIsNone(frappe.get_meta(doc.doctype).get_field("pdf_zip_base64"))
		transient_values = enqueue_files.call_args.args[3]
		self.assertEqual(transient_values["pdf_zip_base64"], "PDF-BASE64")
		self.assertEqual(transient_values["xml_zip_base64"], "XML-BASE64")
		self.assertEqual(transient_values["cdr_zip_base64"], "CDR-BASE64")

		log_payload = frappe.db.get_value(
			"Nubefact API Log",
			{"referencia_guia_de_remision": doc.name},
			"response_payload",
		)
		self.assertEqual(json.loads(log_payload)["pdf_zip_base64"], "PDF-BASE64")

	@patch(
		"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.enqueue_nubefact_file_downloads"
	)
	@patch("nubefact.utils.nubefact.requests.post")
	def test_query_uses_base64_only_for_attachments(self, post, enqueue_files):
		local = self.make_local()
		series = self.make_series(local)
		doc = make_valid_gre(
			company=local.company,
			local=local.name,
			nubefact_series=series.name,
			serie=series.serie,
			numero=None,
		).insert()
		doc.db_set({"numero": 1, "status": "Pendiente de Aceptacion"})
		post.return_value = self.make_http_response(
			{
				"tipo_de_comprobante": 7,
				"serie": series.serie,
				"numero": 1,
				"aceptada_por_sunat": True,
				"cdr_zip_base64": "CDR-BASE64",
			}
		)

		result = refrescar_estado_sunat(doc.name)

		self.assertNotIn("cdr_zip_base64", result)
		self.assertEqual(enqueue_files.call_args.args[3]["cdr_zip_base64"], "CDR-BASE64")
		self.assertIsNone(enqueue_files.call_args.kwargs["response_payload"])

	def test_sunat_error_response_is_terminal_and_keeps_important_note(self):
		doc = make_valid_gre()

		values = doc._extract_response_values(
			{
				"tipo_de_comprobante": 7,
				"serie": "TTT1",
				"numero": 1,
				"aceptada_por_sunat": False,
				"sunat_responsecode": "3617",
				"sunat_description": "La guía fue rechazada",
				"nota_importante": "Revise los datos en SUNAT",
			}
		)

		self.assertEqual(values["status"], "Error")
		self.assertIn("3617", values["error_message"])
		self.assertIn("La guía fue rechazada", values["error_message"])
		self.assertEqual(values["nota_importante"], "Revise los datos en SUNAT")

		note_only = doc._extract_response_values(
			{"aceptada_por_sunat": False, "sunat_note": "Observación sin código de rechazo"}
		)
		self.assertEqual(note_only["status"], "Pendiente de Aceptacion")
		self.assertEqual(note_only["sunat_note"], "Observación sin código de rechazo")
		self.assertEqual(note_only["error_message"], "")

	def test_response_must_match_requested_document(self):
		doc = make_valid_gre()

		with self.assertRaises(frappe.ValidationError):
			doc._extract_response_values(
				{
					"tipo_de_comprobante": 8,
					"serie": "VVV1",
					"numero": 1,
					"aceptada_por_sunat": False,
				}
			)
