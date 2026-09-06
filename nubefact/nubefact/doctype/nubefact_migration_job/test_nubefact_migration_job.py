# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from __future__ import annotations

import base64
import io
import socket
import zipfile
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime, random_string

from nubefact.nubefact.doctype.nubefact_api_log.nubefact_api_log import (
	create_api_log,
	sanitize_migration_log_payload,
)
from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision import (
	enviar_a_nubefact,
	refrescar_estado_sunat,
)
from nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_artifacts import (
	ArtifactValidationError,
	InspectedArtifacts,
	inspect_base64_artifacts,
)
from nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job import (
	OwnershipLost,
	_lock_owned_job,
	_validate_online_route,
	build_consultar_guia_payload,
	cancel_migration,
	interpret_query_response,
	recover_stale_migration_jobs,
	retry_migration,
	run_next_migration_number,
	start_migration,
)
from nubefact.utils.nubefact import NubefactAPIError, make_request

DESPATCH_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>TTT1-00000001</cbc:ID>
</DespatchAdvice>"""
CDR_WITH_REFERENCE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cac:DocumentResponse><cac:DocumentReference><cbc:ID>TTT1-00000001</cbc:ID></cac:DocumentReference></cac:DocumentResponse>
</ApplicationResponse>"""


def zip64(filename: str, content: bytes) -> str:
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(filename, content)
	return base64.b64encode(buffer.getvalue()).decode()


class TestMigrationInterpretation(FrappeTestCase):
	def test_query_payload_is_fixed_to_type_7_consultar_guia(self):
		self.assertEqual(
			build_consultar_guia_payload("ttt1", 12),
			{
				"operacion": "consultar_guia",
				"tipo_de_comprobante": 7,
				"serie": "TTT1",
				"numero": "12",
			},
		)
		with self.assertRaises(frappe.ValidationError):
			build_consultar_guia_payload("VVV1", 12)

	def test_code_24_is_classified_before_document_identity(self):
		result = interpret_query_response(
			{"codigo": 24, "errors": "El documento no existe"},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertEqual(result.kind, "not_found")

	def test_success_requires_explicit_canonical_identity(self):
		for response in (
			{"aceptada_por_sunat": True, "serie": "TTT1", "numero": 1},
			{"aceptada_por_sunat": True, "tipo_de_comprobante": 7, "numero": 1},
			{"aceptada_por_sunat": True, "tipo_de_comprobante": 7, "serie": "TTT1"},
			{"aceptada_por_sunat": True, "tipo_de_comprobante": 8, "serie": "TTT1", "numero": 1},
		):
			with self.subTest(response=response):
				with self.assertRaises(frappe.ValidationError):
					interpret_query_response(response, expected_series="TTT1", expected_number=1)

		result = interpret_query_response(
			{
				"aceptada_por_sunat": True,
				"tipo_de_comprobante": "7",
				"serie": "ttt1",
				"numero": "00000001",
				"enlace_del_xml": "https://example.com/guide.xml",
			},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertEqual(result.kind, "document")

	def test_nonterminal_document_waits_even_if_identity_is_valid(self):
		result = interpret_query_response(
			{
				"aceptada_por_sunat": False,
				"tipo_de_comprobante": 7,
				"serie": "TTT1",
				"numero": 1,
			},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertEqual(result.kind, "waiting")

	def test_base64_labels_are_not_trusted_and_source_identity_is_strict(self):
		artifacts = inspect_base64_artifacts(
			{
				"pdf_zip_base64": zip64("guide.xml", DESPATCH_XML),
				"xml_zip_base64": zip64("guide.pdf", b"%PDF-1.7\nfixture"),
				"cdr_zip_base64": zip64("R-guide.xml", CDR_WITH_REFERENCE),
			},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertEqual(artifacts.logical["pdf"], b"%PDF-1.7\nfixture")
		self.assertEqual(artifacts.logical["xml"], DESPATCH_XML)
		self.assertEqual(artifacts.logical["cdr"], CDR_WITH_REFERENCE)
		self.assertEqual(set(artifacts.containers), {"pdf_zip_base64", "xml_zip_base64", "cdr_zip_base64"})

		invalid = inspect_base64_artifacts(
			{"xml_zip_base64": zip64("guide.xml", DESPATCH_XML.replace(b"TTT1", b"TTT2"))},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertIn("xml", invalid.errors)
		self.assertNotIn("xml", invalid.logical)

	def test_optional_artifact_errors_and_conflicts_are_scoped_by_kind(self):
		artifacts = inspect_base64_artifacts(
			{
				"pdf_zip_base64": "not-base64",
				"xml_zip_base64": zip64("guide.xml", DESPATCH_XML),
				"cdr_zip_base64": zip64("R-guide.xml", CDR_WITH_REFERENCE),
			},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertEqual(artifacts.logical["xml"], DESPATCH_XML)
		self.assertEqual(artifacts.logical["cdr"], CDR_WITH_REFERENCE)
		self.assertIn("pdf", artifacts.errors)

		conflicting = inspect_base64_artifacts(
			{
				"pdf_zip_base64": zip64("one.pdf", b"%PDF-one"),
				"cdr_zip_base64": zip64("two.pdf", b"%PDF-two"),
				"xml_zip_base64": zip64("guide.xml", DESPATCH_XML),
			},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertIn("pdf", conflicting.errors)
		self.assertNotIn("pdf", conflicting.logical)
		self.assertEqual(conflicting.logical["xml"], DESPATCH_XML)

	def test_nested_archives_are_rejected_by_magic_and_cdr_reference_is_validated(self):
		# Use actual ZIP bytes under a non-archive extension.
		inner = io.BytesIO()
		with zipfile.ZipFile(inner, "w") as archive:
			archive.writestr("guide.xml", DESPATCH_XML)
		outer = io.BytesIO()
		with zipfile.ZipFile(outer, "w") as archive:
			archive.writestr("payload.bin", inner.getvalue())
		result = inspect_base64_artifacts(
			{"xml_zip_base64": base64.b64encode(outer.getvalue()).decode()},
			expected_series="TTT1",
			expected_number=1,
		)
		self.assertIn("xml", result.errors)

		mismatched_cdr = CDR_WITH_REFERENCE.replace(b"TTT1-00000001", b"TTT1-00000002")
		for cdr in (
			mismatched_cdr,
			b'<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2" />',
		):
			result = inspect_base64_artifacts(
				{"cdr_zip_base64": zip64("R-guide.xml", cdr)},
				expected_series="TTT1",
				expected_number=1,
			)
			self.assertIn("cdr", result.errors)


class TestMigrationManagerAndWorker(FrappeTestCase):
	def test_server_populated_fields_do_not_block_standard_form_save(self):
		meta = frappe.get_meta("Nubefact Migration Job")
		for fieldname in ("serie", "requested_by"):
			self.assertFalse(meta.get_field(fieldname).reqd)

	def make_job(self, *, start=1, end=2):
		company = frappe.get_all("Company", pluck="name", limit=1)[0]
		local = frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": f"Migration {random_string(7)}",
				"company": company,
				"ruta_api": "https://8.8.8.8/gre",
				"token_api": "test-token",
			}
		).insert()
		while True:
			series_code = f"T{random_string(3).upper()}"
			if not frappe.db.exists(
				"Nubefact Series",
				{"company": company, "tipo_de_comprobante": "7", "serie": series_code},
			):
				break
		series = frappe.get_doc(
			{
				"doctype": "Nubefact Series",
				"company": company,
				"local": local.name,
				"tipo_de_comprobante": "7",
				"serie": series_code,
				"numero": 200,
			}
		).insert()
		job = frappe.get_doc(
			{
				"doctype": "Nubefact Migration Job",
				"company": company,
				"local": local.name,
				"nubefact_series": series.name,
				"from_number": start,
				"to_number": end,
			}
		).insert()
		return job, series

	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job._dispatch_job")
	def test_start_cancel_and_retry_are_server_managed(self, dispatch):
		job, _series = self.make_job()
		start_migration(job.name)
		job.reload()
		self.assertEqual(job.status, "Queued")
		self.assertEqual(job.tipo_de_comprobante, "7")
		self.assertEqual(job.total_count, 2)
		self.assertGreater(
			frappe.db.count("Version", {"ref_doctype": job.doctype, "docname": job.name}),
			0,
		)
		dispatch.assert_called_once_with(job.name)

		cancel_migration(job.name)
		job.reload()
		self.assertTrue(job.cancel_requested)

		frappe.db.set_value(
			job.doctype,
			job.name,
			{
				"status": "Cancelled",
				"worker_token": "",
				"lease_expires_at": None,
			},
		)
		retry_migration(job.name)
		job.reload()
		self.assertEqual(job.status, "Queued")
		self.assertFalse(job.cancel_requested)

	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job._dispatch_job")
	@patch(
		"nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job.collect_response_artifacts"
	)
	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job.make_request")
	def test_worker_recreates_historical_gre_and_never_moves_series_backward(
		self, request, collect, dispatch
	):
		from nubefact.nubefact.doctype.nubefact_guia_de_remision.test_nubefact_guia_de_remision_import_xml import (
			DESPATCH_XML as COMPLETE_XML,
		)

		job, series = self.make_job(start=199, end=199)
		xml = (
			COMPLETE_XML.format(
				series=series.serie,
				packages="<cbc:TotalTransportHandlingUnitQuantity>3</cbc:TotalTransportHandlingUnitQuantity>",
			)
			.replace(f"{series.serie}-25", f"{series.serie}-00000199")
			.encode()
		)
		request.return_value = {
			"tipo_de_comprobante": 7,
			"serie": series.serie.lower(),
			"numero": "00000199",
			"aceptada_por_sunat": True,
			"sunat_responsecode": "0",
		}
		collect.return_value = InspectedArtifacts(logical={"xml": xml})
		start_migration(job.name)
		dispatch.reset_mock()

		run_next_migration_number(job.name)

		job.reload()
		series.reload()
		self.assertEqual(job.status, "Completed with Warnings")
		self.assertEqual(job.created_count, 1)
		self.assertEqual(series.numero, 200)
		self.assertGreaterEqual(series.ultimo_numero_asignado, 199)
		gre = frappe.get_doc("Nubefact Guia De Remision", job.results[0].guia_de_remision)
		self.assertTrue(gre.migrated_from_nubefact)
		self.assertEqual(gre.migration_job, job.name)
		self.assertTrue(gre.issued_identity_hash)
		self.assertEqual(gre.fecha_de_emision.isoformat(), "2026-06-01")
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": gre.doctype, "attached_to_name": gre.name},
			fields=["file_name", "is_private"],
		)
		self.assertEqual(len(files), 1)
		self.assertTrue(all(row.is_private for row in files))
		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden eliminar"):
			gre.delete()

	def test_migrated_gre_cannot_be_sent_again(self):
		job, series = self.make_job(start=1, end=1)
		gre = frappe.get_doc(
			{
				"doctype": "Nubefact Guia De Remision",
				"company": job.company,
				"local": job.local,
				"nubefact_series": series.name,
				"tipo_de_comprobante": "7",
				"serie": series.serie,
				"numero": 1,
				"skip_field_validation": 1,
			}
		).insert()
		frappe.db.set_value(
			gre.doctype,
			gre.name,
			{"migrated_from_nubefact": 1, "migration_job": job.name},
			update_modified=False,
		)
		with self.assertRaisesRegex(frappe.ValidationError, "migrada"):
			enviar_a_nubefact(gre.name)
		with (
			patch(
				"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.make_request",
				return_value={
					"tipo_de_comprobante": 7,
					"serie": series.serie,
					"numero": 1,
					"aceptada_por_sunat": True,
				},
			) as request,
			patch(
				"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.enqueue_nubefact_file_downloads"
			),
		):
			refrescar_estado_sunat(gre.name)
		self.assertEqual(request.call_args.kwargs["migration_job"], job.name)
		gre.reload()
		gre.observaciones = "forged update"
		with self.assertRaisesRegex(frappe.ValidationError, "inmutables"):
			gre.save()

	def test_owned_lock_requires_token_and_live_lease(self):
		job, _series = self.make_job(start=1, end=1)
		frappe.db.set_value(
			job.doctype,
			job.name,
			{
				"status": "Queued",
				"worker_token": "worker-one",
				"lease_expires_at": add_to_date(now_datetime(), seconds=-1),
			},
		)
		with self.assertRaises(OwnershipLost):
			_lock_owned_job(job.name, "worker-one")
		frappe.db.rollback()

	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job._get_active_job_names")
	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job._dispatch_job")
	def test_stale_recovery_locks_reserves_and_honors_earliest_retry(self, dispatch, active_jobs):
		job, _series = self.make_job(start=1, end=2)
		start_migration(job.name)
		active_jobs.return_value = [job.name]
		dispatch.reset_mock()
		item = frappe.get_doc(
			{
				"doctype": "Nubefact Migration Job Item",
				"parent": job.name,
				"parenttype": job.doctype,
				"parentfield": "results",
				"number": 1,
				"status": "Waiting for Artifacts",
				"retry_after": add_to_date(now_datetime(), minutes=5),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			job.doctype,
			job.name,
			{
				"current_number": 0,
				"worker_token": "expired",
				"lease_expires_at": add_to_date(now_datetime(), seconds=-1),
			},
		)

		recover_stale_migration_jobs()
		dispatch.assert_not_called()

		frappe.db.set_value(item.doctype, item.name, "retry_after", add_to_date(now_datetime(), seconds=-1))
		recover_stale_migration_jobs()
		dispatch.assert_called_once()
		reserved_token = dispatch.call_args.kwargs["worker_token"]
		job.reload()
		self.assertEqual(job.worker_token, reserved_token)
		self.assertGreater(job.lease_expires_at, now_datetime())

		dispatch.reset_mock()
		recover_stale_migration_jobs()
		dispatch.assert_not_called()

	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job._dispatch_job")
	@patch("nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job.make_request")
	def test_each_worker_invocation_processes_and_chains_one_number(self, request, dispatch):
		def query_not_found(*_args, **kwargs):
			kwargs["log_callback"]("LOG-EXACT")
			return {"codigo": 24, "errors": "no existe"}

		request.side_effect = query_not_found
		job, _series = self.make_job(start=1, end=2)
		start_migration(job.name)
		dispatch.reset_mock()

		run_next_migration_number(job.name)

		job.reload()
		self.assertEqual(request.call_count, 1)
		self.assertEqual(
			job.processed_count,
			1,
			msg=f"status={job.status}, error={job.last_error}, results={[(r.number, r.status, r.message) for r in job.results]}",
		)
		self.assertEqual(job.status, "Queued")
		self.assertEqual([row.number for row in job.results], [1])
		self.assertEqual(job.results[0].api_log, "LOG-EXACT")
		dispatch.assert_called_once_with(job.name)

	def test_migration_jobs_and_api_logs_are_immutable_audit_records(self):
		job, _series = self.make_job(start=1, end=1)
		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden eliminar"):
			job.delete()
		forged_log = frappe.get_doc(
			{
				"doctype": "Nubefact API Log",
				"migration_job": job.name,
				"request_payload": '{"xml_zip_base64": "SECRET"}',
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "sólo pueden ser creados por el servidor"):
			forged_log.insert(ignore_permissions=True)

		log_name = create_api_log(
			"consultar_guia",
			job.local,
			"https://8.8.8.8/gre",
			None,
			None,
			now_datetime(),
			{"operacion": "consultar_guia"},
			now_datetime(),
			200,
			{"codigo": 24},
			"OK",
			None,
			None,
			1,
			migration_job=job.name,
		)
		log = frappe.get_doc("Nubefact API Log", log_name)
		log.migration_job = ""
		with self.assertRaisesRegex(frappe.ValidationError, "inmutables"):
			log.save()
		log.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden eliminar"):
			log.delete()


class TestStructuredAPIError(FrappeTestCase):
	@patch("nubefact.utils.nubefact.create_api_log", return_value="LOG-1")
	@patch("nubefact.utils.nubefact.get_request_config")
	@patch("nubefact.utils.nubefact.requests.post")
	def test_http_metadata_and_migration_log_sanitization(self, post, get_config, create_log):
		local = Mock(name="LOCAL-1")
		local.name = "LOCAL-1"
		get_config.return_value = (local, "https://api.example.test", "secret")
		response = Mock(status_code=429, ok=False, text="")
		response.json.return_value = {
			"codigo": 40,
			"errors": "temporarily unavailable",
			"xml_zip_base64": "secret-base64",
		}
		post.return_value = response

		with self.assertRaises(NubefactAPIError) as raised:
			make_request(
				{"operacion": "consultar_guia"},
				"LOCAL-1",
				migration_job="MIG-GRE-2026-000001",
			)

		self.assertEqual(raised.exception.http_status, 429)
		self.assertTrue(raised.exception.retryable)
		logged = create_log.call_args.kwargs["response_payload"]
		self.assertNotIn("secret-base64", str(logged))
		self.assertEqual(logged["xml_zip_base64"]["encoded_length"], len("secret-base64"))

	@patch("nubefact.utils.nubefact.create_api_log", return_value="LOG-1")
	@patch("nubefact.utils.nubefact.get_request_config")
	@patch("nubefact.utils.nubefact.requests.post")
	def test_http_403_is_fatal_and_log_guard_fences_persistence(self, post, get_config, create_log):
		local = Mock(name="LOCAL-1")
		local.name = "LOCAL-1"
		get_config.return_value = (local, "https://api.example.test", "secret")
		response = Mock(status_code=403, ok=False, text="forbidden")
		response.json.side_effect = ValueError
		post.return_value = response
		guard = Mock(side_effect=OwnershipLost)

		with self.assertRaises(OwnershipLost):
			make_request(
				{"operacion": "consultar_guia"},
				"LOCAL-1",
				None,
				None,
				60,
				migration_job="MIG-GRE-2026-000001",
				log_guard=guard,
			)
		guard.assert_called_once_with()
		create_log.assert_not_called()

		guard.side_effect = None
		with self.assertRaises(NubefactAPIError) as raised:
			make_request(
				{"operacion": "consultar_guia"},
				"LOCAL-1",
				None,
				None,
				60,
				migration_job="MIG-GRE-2026-000001",
				log_guard=guard,
			)
		self.assertTrue(raised.exception.fatal)

	def test_migration_log_sanitizer_never_keeps_raw_non_objects_or_large_base64_text(self):
		raw = "A" * 20_000
		non_object = sanitize_migration_log_payload(raw)
		self.assertIsInstance(non_object, dict)
		self.assertNotIn(raw[:100], str(non_object))
		self.assertEqual(non_object["length"], len(raw))

		sanitized = sanitize_migration_log_payload({"nested": {"blob": raw}})
		self.assertNotIn(raw[:100], str(sanitized))
		self.assertEqual(sanitized["nested"]["blob"]["length"], len(raw))

	@patch("nubefact.utils.socket.getaddrinfo")
	def test_api_route_rejects_hostnames_resolving_to_any_non_global_address(self, getaddrinfo):
		getaddrinfo.return_value = [
			(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
			(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
		]
		with self.assertRaises(frappe.ValidationError):
			_validate_online_route("https://api.example.test/v1/account")
