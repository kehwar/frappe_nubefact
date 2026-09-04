# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


class TestNubefactLocal(FrappeTestCase):
	def setUp(self):
		self.company = frappe.get_all("Company", fields=["name", "abbr"], limit=1)[0]

	def make_local(self, title):
		return frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": title,
				"company": self.company.name,
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
