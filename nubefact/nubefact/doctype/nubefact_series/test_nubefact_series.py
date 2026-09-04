# Copyright (c) 2026, Erick W.R. and contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from nubefact.nubefact.doctype.nubefact_series.nubefact_series import allocate_document_number


class TestNubefactSeries(FrappeTestCase):
	def make_company(self):
		company = frappe.get_all("Company", pluck="name", limit=1)
		if not company:
			self.skipTest("Company DocType has no test fixture")
		return company[0]

	def make_local(self, company=None):
		return frappe.get_doc(
			{
				"doctype": "Nubefact Local",
				"title": f"Local Series {random_string(8)}",
				"company": company or self.make_company(),
			}
		).insert()

	def test_company_document_type_and_series_are_unique(self):
		company = self.make_company()
		local = self.make_local(company)
		values = {
			"doctype": "Nubefact Series",
			"company": company,
			"local": local.name,
			"tipo_de_comprobante": "1",
			"serie": f"F{random_string(3).upper()}",
			"numero": 41,
		}
		series = frappe.get_doc(values).insert()

		self.assertEqual(series.numero, 41)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({**values, "local": self.make_local(company).name}).insert()

		other_document_type = frappe.get_doc(
			{
				**values,
				"tipo_de_comprobante": "3",
			}
		).insert()
		self.assertNotEqual(other_document_type.name, series.name)

		document = frappe.get_doc(
			{
				"doctype": "Nubefact Guia De Remision",
				"company": company,
				"local": local.name,
				"nubefact_series": frappe.get_doc(
					{
						**values,
						"tipo_de_comprobante": "7",
						"serie": f"T{random_string(3).upper()}",
					}
				).insert().name,
				"skip_field_validation": 1,
			}
		).insert()

		self.assertEqual(allocate_document_number(document), 41)
		self.assertEqual(document.numero, 41)
		self.assertEqual(frappe.db.get_value(document.doctype, document.name, "numero"), 41)
		self.assertEqual(frappe.db.get_value("Nubefact Series", document.nubefact_series, "numero"), 42)

		imported = frappe.get_doc(
			{
				"doctype": "Nubefact Guia De Remision",
				"company": company,
				"local": local.name,
				"nubefact_series": document.nubefact_series,
				"numero": 55,
				"skip_field_validation": 1,
			}
		).insert()
		self.assertEqual(allocate_document_number(imported), 55)
		self.assertEqual(frappe.db.get_value("Nubefact Series", document.nubefact_series, "numero"), 56)

	def test_facturacion_must_match_the_selected_series_identity(self):
		company = self.make_company()
		local = self.make_local(company)
		other_local = self.make_local(company)
		series = frappe.get_doc(
			{
				"doctype": "Nubefact Series",
				"company": company,
				"local": local.name,
				"tipo_de_comprobante": "1",
				"serie": f"F{random_string(3).upper()}",
				"numero": 1,
			}
		).insert()

		document = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion",
				"nubefact_series": series.name,
				"skip_field_validation": 1,
			}
		).insert()
		self.assertEqual(document.company, company)
		self.assertEqual(document.local, local.name)
		self.assertEqual(document.tipo_de_comprobante, "1")
		self.assertEqual(document.serie, series.serie)

		mismatched = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion",
				"company": company,
				"local": other_local.name,
				"nubefact_series": series.name,
				"skip_field_validation": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			mismatched.insert()

		mismatched_type = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion",
				"nubefact_series": series.name,
				"tipo_de_comprobante": "2",
				"skip_field_validation": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			mismatched_type.insert()

	def test_local_must_belong_to_company(self):
		local = self.make_local()
		other_company = frappe.get_all("Company", filters={"name": ["!=", local.company]}, pluck="name", limit=1)
		if not other_company:
			self.skipTest("A second Company fixture is required")

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Nubefact Series",
					"company": other_company[0],
					"local": local.name,
					"tipo_de_comprobante": "1",
					"serie": f"F{random_string(3).upper()}",
					"numero": 1,
				}
			).insert()
