# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from __future__ import annotations

import base64
import json
from unittest.mock import Mock, patch

import frappe
import requests
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion import send_to_nubefact
from nubefact.utils import (
	attach_nubefact_base64_file,
	attach_nubefact_json,
	download_and_attach_file,
	enqueue_nubefact_file_downloads,
)


class TestNubefactFacturacion(FrappeTestCase):
	def make_local_and_series(self, *, numero=1):
		company = frappe.get_all("Company", pluck="name", limit=1)[0]
		local = frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": f"Local CPE {random_string(8)}",
				"company": company,
				"ruta_api": "https://api.example.test/cpe",
				"token_api": "test-token",
			}
		).insert()
		series = frappe.get_doc(
			{
				"doctype": "Nubefact Series",
				"company": company,
				"local": local.name,
				"tipo_de_comprobante": "1",
				"serie": f"F{random_string(3).upper()}",
				"numero": numero,
			}
		).insert()
		return local, series

	@staticmethod
	def make_http_response(payload):
		response = Mock(status_code=200, ok=True, text="")
		response.json.return_value = payload
		return response

	@patch(
		"nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion.enqueue_nubefact_file_downloads"
	)
	@patch("nubefact.utils.nubefact.requests.post")
	def test_issue_assigns_initial_number_and_advances_tracker(self, post, enqueue_files):
		local, series = self.make_local_and_series(numero=17)
		document = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion",
				"company": local.company,
				"local": local.name,
				"nubefact_series": series.name,
				"tipo_de_comprobante": "1",
				"numero": None,
				"skip_field_validation": 1,
			}
		).insert()
		post.return_value = self.make_http_response(
			{
				"tipo_de_comprobante": 1,
				"serie": series.serie,
				"numero": 17,
				"aceptada_por_sunat": True,
			}
		)

		result = send_to_nubefact(document.name)

		self.assertEqual(result["status"], "Aceptada")
		self.assertEqual(frappe.db.get_value(document.doctype, document.name, "numero"), 17)
		self.assertEqual(frappe.db.get_value(series.doctype, series.name, "numero"), 18)
		self.assertEqual(post.call_args.kwargs["json"]["numero"], 17)
		self.assertEqual(enqueue_files.call_args.kwargs["request_payload"]["numero"], 17)
		self.assertEqual(enqueue_files.call_args.kwargs["response_payload"]["numero"], 17)

	@patch("nubefact.utils.nubefact.requests.post")
	def test_failed_issue_reuses_reserved_number_on_retry(self, post):
		local, series = self.make_local_and_series(numero=30)
		document = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion",
				"company": local.company,
				"local": local.name,
				"nubefact_series": series.name,
				"tipo_de_comprobante": "1",
				"skip_field_validation": 1,
			}
		).insert()
		post.side_effect = [
			requests.Timeout("timeout"),
			self.make_http_response(
				{
					"tipo_de_comprobante": 1,
					"serie": series.serie,
					"numero": 30,
					"aceptada_por_sunat": True,
				}
			),
		]

		failed = send_to_nubefact(document.name)
		self.assertEqual(failed["status"], "Error")
		self.assertEqual(frappe.db.get_value(document.doctype, document.name, "numero"), 30)
		self.assertEqual(frappe.db.get_value(series.doctype, series.name, "numero"), 31)

		succeeded = send_to_nubefact(document.name)
		self.assertEqual(succeeded["status"], "Aceptada")
		self.assertEqual(frappe.db.get_value(series.doctype, series.name, "numero"), 31)
		self.assertEqual(post.call_args.kwargs["json"]["numero"], 30)

	def test_response_identity_must_match_allocated_number(self):
		document = frappe.new_doc("Nubefact Facturacion")
		document.tipo_de_comprobante = "1"
		document.serie = "F001"
		document.numero = 17

		with self.assertRaises(frappe.ValidationError):
			document._extract_response_values(
				{
					"tipo_de_comprobante": 1,
					"serie": "F001",
					"numero": 18,
				}
			)

		values = document._extract_response_values(
			{
				"tipo_de_comprobante": 1,
				"serie": "F001",
				"numero": 17,
				"aceptada_por_sunat": True,
			}
		)
		self.assertNotIn("pdf_zip_base64", values)
		self.assertNotIn("enlace_del_pdf", values)

	@patch("nubefact.utils.frappe.enqueue")
	def test_issue_attachments_are_queued_after_commit(self, enqueue):
		payload = {"operacion": "generar_comprobante", "numero": 17}
		response_payload = {"numero": 17, "aceptada_por_sunat": True}
		values = {
			"enlace_del_pdf": "https://files.example.test/doc.pdf",
			"enlace_del_xml": "https://files.example.test/doc.xml",
			"enlace_del_cdr": "https://files.example.test/doc.cdr",
			"pdf_zip_base64": "fallback",
		}

		enqueue_nubefact_file_downloads(
			"Nubefact Facturacion",
			"CPE-TEST",
			"F001-17",
			values,
			request_payload=payload,
			response_payload=response_payload,
		)

		self.assertEqual(enqueue.call_count, 5)
		json_jobs = {
			call.kwargs["filename"]: call.kwargs
			for call in enqueue.call_args_list
			if call.args[0] == "nubefact.utils.attach_nubefact_json"
		}
		self.assertEqual(json_jobs["F001-17-request.json"]["payload"], payload)
		self.assertEqual(
			json_jobs["F001-17-response.json"]["payload"], response_payload
		)
		download_jobs = [
			call.kwargs
			for call in enqueue.call_args_list
			if call.args[0] == "nubefact.utils.download_and_attach_file"
		]
		self.assertEqual(
			{job["filename"] for job in download_jobs},
			{"F001-17.pdf", "F001-17.xml", "F001-17.cdr"},
		)
		self.assertTrue(
			all(call.kwargs["enqueue_after_commit"] for call in enqueue.call_args_list)
		)

	@patch("nubefact.utils.save_file")
	@patch("nubefact.utils._attachment_exists", return_value=False)
	def test_json_and_base64_files_are_private_attachments(self, _exists, save_file):
		payload = {"operacion": "generar_comprobante", "numero": 17}
		attach_nubefact_json(
			payload,
			"F001-17-request.json",
			"Nubefact Facturacion",
			"CPE-TEST",
		)
		json_call = save_file.call_args_list[0].kwargs
		self.assertEqual(json.loads(json_call["content"]), payload)
		self.assertEqual(json_call["is_private"], 1)

		encoded_zip = base64.b64encode(b"zip-content").decode()
		with patch("nubefact.utils.frappe.db.get_value", return_value=encoded_zip):
			attach_nubefact_base64_file(
				"pdf_zip_base64",
				"F001-17-pdf.zip",
				"Nubefact Facturacion",
				"CPE-TEST",
			)
		base64_call = save_file.call_args_list[1].kwargs
		self.assertEqual(base64_call["content"], b"zip-content")
		self.assertEqual(base64_call["is_private"], 1)

	@patch("nubefact.utils.save_file")
	@patch("nubefact.utils._attachment_exists", return_value=False)
	@patch("nubefact.utils.requests.get")
	@patch("nubefact.utils.socket.getaddrinfo")
	def test_downloads_only_public_urls_as_private_attachments(
		self, getaddrinfo, get, _exists, save_file
	):
		getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
		response = Mock(status_code=200, headers={}, content=b"pdf-content")
		response.raise_for_status.return_value = None
		get.return_value = response

		download_and_attach_file(
			"https://files.example.test/doc.pdf",
			"F001-17.pdf",
			"Nubefact Facturacion",
			"CPE-TEST",
		)

		get.assert_called_once_with(
			"https://files.example.test/doc.pdf", timeout=60, allow_redirects=False
		)
		self.assertEqual(save_file.call_args.kwargs["content"], b"pdf-content")
		self.assertEqual(save_file.call_args.kwargs["is_private"], 1)

		get.reset_mock()
		save_file.reset_mock()
		getaddrinfo.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
		with patch("nubefact.utils.frappe.log_error"):
			download_and_attach_file(
				"https://localhost/private",
				"blocked.pdf",
				"Nubefact Facturacion",
				"CPE-TEST",
			)
		get.assert_not_called()
		save_file.assert_not_called()
