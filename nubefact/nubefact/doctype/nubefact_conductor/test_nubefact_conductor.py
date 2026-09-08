# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


class TestNubefactConductor(FrappeTestCase):
	def make_conductor(self, **overrides):
		values = {
			"doctype": "Nubefact Conductor",
			"documento_tipo": "1",
			"documento_numero": random_string(8).upper(),
			"numero_licencia": random_string(9).upper(),
			"nombre": "JUAN",
			"apellidos": "PEREZ",
			"denominacion": "CONDUCTOR PRINCIPAL",
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def test_identity_is_normalized_and_used_as_name(self):
		document_number = random_string(8).upper()
		license_number = random_string(9).upper()
		doc = self.make_conductor(
			documento_numero=f" {document_number.lower()} ",
			numero_licencia=f" {license_number.lower()} ",
			nombre=" Juan ",
			apellidos=" Perez ",
		).insert()

		self.assertEqual(doc.name, f"1-{document_number}")
		self.assertEqual(doc.documento_numero, document_number)
		self.assertEqual(doc.numero_licencia, license_number)
		self.assertEqual(doc.nombre_completo, "Juan Perez")

	def test_vehicle_is_optional_and_can_be_linked(self):
		plate = f"V{random_string(5)}".upper()
		frappe.get_doc({"doctype": "Nubefact Vehiculo", "placa_numero": plate}).insert()

		doc = self.make_conductor(vehiculo=plate).insert()

		self.assertEqual(doc.vehiculo, plate)

	def test_document_type_must_apply_to_drivers(self):
		doc = self.make_conductor(documento_tipo="6")

		with self.assertRaisesRegex(frappe.ValidationError, "catálogo de conductores"):
			doc.insert()

	def test_license_format_is_validated(self):
		doc = self.make_conductor(numero_licencia="Q-12345678")

		with self.assertRaisesRegex(frappe.ValidationError, "9 a 10"):
			doc.insert()

	def test_document_identity_cannot_change_after_creation(self):
		doc = self.make_conductor().insert()
		doc.documento_numero = random_string(8).upper()

		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden cambiar"):
			doc.save()
