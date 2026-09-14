# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from nubefact.patches.backfill_nubefact_vehiculo_titles import execute as backfill_vehicle_titles


class TestNubefactVehiculo(FrappeTestCase):
	def test_plate_is_normalized_and_used_as_name_and_default_title(self):
		plate = f"A{random_string(5)}".upper()
		doc = frappe.get_doc({"doctype": "Nubefact Vehiculo", "placa_numero": f" {plate.lower()} "}).insert()

		self.assertEqual(doc.placa_numero, plate)
		self.assertEqual(doc.name, plate)
		self.assertEqual(doc.title, plate)

	def test_optional_title_is_normalized_and_used_for_link_display(self):
		plate = f"T{random_string(5)}".upper()
		doc = frappe.get_doc(
			{"doctype": "Nubefact Vehiculo", "placa_numero": plate, "title": " Camión principal "}
		).insert()

		self.assertEqual(doc.title, "Camión principal")
		self.assertEqual(frappe.get_meta(doc.doctype).title_field, "title")

	def test_blank_title_is_replaced_with_plate(self):
		plate = f"W{random_string(5)}".upper()
		doc = frappe.get_doc({"doctype": "Nubefact Vehiculo", "placa_numero": plate, "title": "   "}).insert()

		self.assertEqual(doc.title, plate)

	def test_patch_backfills_only_blank_existing_titles(self):
		plate = f"P{random_string(5)}".upper()
		doc = frappe.get_doc(
			{"doctype": "Nubefact Vehiculo", "placa_numero": plate, "title": "Temporary title"}
		).insert()
		frappe.db.set_value(doc.doctype, doc.name, "title", "", update_modified=False)

		custom_title_doc = frappe.get_doc(
			{
				"doctype": "Nubefact Vehiculo",
				"placa_numero": f"C{random_string(5)}".upper(),
				"title": "Custom title",
			}
		).insert()

		backfill_vehicle_titles()
		doc.reload()
		custom_title_doc.reload()

		self.assertEqual(doc.title, plate)
		self.assertEqual(custom_title_doc.title, "Custom title")

	def test_invalid_plate_is_rejected(self):
		doc = frappe.get_doc({"doctype": "Nubefact Vehiculo", "placa_numero": "ABC-123"})

		with self.assertRaisesRegex(frappe.ValidationError, "sin guiones"):
			doc.insert()

	def test_plate_cannot_change_after_creation(self):
		plate = f"B{random_string(5)}".upper()
		doc = frappe.get_doc({"doctype": "Nubefact Vehiculo", "placa_numero": plate}).insert()
		doc.placa_numero = f"C{random_string(5)}".upper()

		with self.assertRaisesRegex(frappe.ValidationError, "no se puede cambiar"):
			doc.save()
