import frappe
from frappe.tests.utils import FrappeTestCase

from nubefact.nubefact.doctype.nubefact_ubigeo.nubefact_ubigeo import (
	EXPECTED_UBIGEO_COUNT,
	get_ubigeo_records,
	load_ubigeos,
)


class TestNubefactUbigeo(FrappeTestCase):
	def test_bundled_inei_catalog_is_complete_and_unique(self):
		records = get_ubigeo_records()

		self.assertEqual(len(records), EXPECTED_UBIGEO_COUNT)
		self.assertEqual(len({record["codigo"] for record in records}), EXPECTED_UBIGEO_COUNT)

	def test_catalog_is_loaded_idempotently(self):
		load_ubigeos()
		load_ubigeos()

		self.assertEqual(frappe.db.count("Nubefact Ubigeo"), EXPECTED_UBIGEO_COUNT)
		self.assertEqual(
			frappe.db.get_value(
				"Nubefact Ubigeo",
				"010101",
				["codigo", "departamento", "provincia", "distrito"],
				as_dict=True,
			),
			{
				"codigo": "010101",
				"departamento": "AMAZONAS",
				"provincia": "CHACHAPOYAS",
				"distrito": "CHACHAPOYAS",
			},
		)
		self.assertEqual(
			frappe.db.get_value("Nubefact Ubigeo", "130112", "distrito"),
			"ALTO TRUJILLO",
		)
		self.assertEqual(
			frappe.db.get_value("Nubefact Ubigeo", "250401", "distrito"),
			"PURUS",
		)

	def test_document_name_and_title_use_the_official_code(self):
		doc = frappe.get_doc("Nubefact Ubigeo", "010101")

		self.assertEqual(doc.name, doc.codigo)
		self.assertEqual(doc.title, "010101 - AMAZONAS - CHACHAPOYAS - CHACHAPOYAS")

	def test_non_inei_codes_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Nubefact Ubigeo",
					"codigo": "999999",
					"departamento": "Departamento",
					"provincia": "Provincia",
					"distrito": "Distrito",
				}
			).insert()

	def test_loader_repairs_catalog_drift(self):
		frappe.db.set_value("Nubefact Ubigeo", "010101", "distrito", "Incorrecto")

		load_ubigeos()

		self.assertEqual(
			frappe.db.get_value("Nubefact Ubigeo", "010101", "distrito"),
			"CHACHAPOYAS",
		)

	def test_gre_ubigeos_are_links_to_catalog(self):
		meta = frappe.get_meta("Nubefact Guia De Remision")
		for fieldname in ("punto_de_partida_ubigeo", "punto_de_llegada_ubigeo"):
			field = meta.get_field(fieldname)
			self.assertEqual(field.fieldtype, "Link")
			self.assertEqual(field.options, "Nubefact Ubigeo")
