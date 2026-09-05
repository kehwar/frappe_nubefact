# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from nubefact.nubefact.doctype.nubefact_ubigeo.nubefact_ubigeo import load_ubigeos


class TestNubefactLocal(FrappeTestCase):
	def setUp(self):
		self.company = frappe.get_all("Company", fields=["name", "abbr"], limit=1)[0]
		load_ubigeos()

	def make_local(self, title, **values):
		return frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": title,
				"company": self.company.name,
				**values,
			}
		).insert()

	def test_autoname_uses_title_and_company_abbreviation(self):
		title = f"Local {random_string(8)}"

		local = self.make_local(title)

		self.assertEqual(local.name, f"{title}-{self.company.abbr}")

	def test_autoname_adds_numeric_suffix_on_collision(self):
		title = f"Local {random_string(8)}"

		first_local = self.make_local(title)
		second_local = self.make_local(title)

		self.assertEqual(first_local.name, f"{title}-{self.company.abbr}")
		self.assertEqual(second_local.name, f"{title}-{self.company.abbr}-1")

	def test_local_can_be_renamed(self):
		local = self.make_local(f"Local {random_string(8)}")
		new_name = f"Renamed Local {random_string(8)}"

		rename_result = frappe.rename_doc("Nubefact Local", local.name, new_name)

		self.assertEqual(rename_result, new_name)
		self.assertTrue(frappe.db.exists("Nubefact Local", new_name))

	def test_ubigeo_populates_read_only_location_fields(self):
		local = self.make_local(
			f"Local {random_string(8)}",
			ubigeo="150101",
			departamento="IGNORED",
			provincia="IGNORED",
			distrito="IGNORED",
		)

		self.assertEqual(local.departamento, "LIMA")
		self.assertEqual(local.provincia, "LIMA")
		self.assertEqual(local.distrito, "LIMA")

	def test_ubigeo_and_location_field_metadata(self):
		meta = frappe.get_meta("Nubefact Local")
		ubigeo = meta.get_field("ubigeo")
		self.assertEqual(ubigeo.fieldtype, "Link")
		self.assertEqual(ubigeo.options, "Nubefact Ubigeo")

		for fieldname in ("departamento", "provincia", "distrito"):
			field = meta.get_field(fieldname)
			self.assertTrue(field.read_only)
			self.assertEqual(field.fetch_from, f"ubigeo.{fieldname}")
