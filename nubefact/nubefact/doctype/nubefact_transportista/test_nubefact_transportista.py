# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

from random import randint

import frappe
from frappe.tests.utils import FrappeTestCase


def random_ruc():
	return f"20{randint(100_000_000, 999_999_999)}"


class TestNubefactTransportista(FrappeTestCase):
	def make_transportista(self, **overrides):
		values = {
			"doctype": "Nubefact Transportista",
			"documento_tipo": "6",
			"documento_numero": random_ruc(),
			"denominacion": "TRANSPORTES DE PRUEBA SAC",
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def test_identity_is_normalized_and_used_as_name(self):
		ruc = random_ruc()
		doc = self.make_transportista(
			documento_numero=f" {ruc} ",
			denominacion=" Transportes de Prueba SAC ",
		).insert()

		self.assertEqual(doc.name, f"6-{ruc}")
		self.assertEqual(doc.documento_numero, ruc)
		self.assertEqual(doc.denominacion, "Transportes de Prueba SAC")

	def test_document_type_must_be_ruc(self):
		doc = self.make_transportista(documento_tipo="1")

		with self.assertRaisesRegex(frappe.ValidationError, "debe ser 6"):
			doc.insert()

	def test_ruc_must_have_eleven_digits(self):
		doc = self.make_transportista(documento_numero="12345678")

		with self.assertRaisesRegex(frappe.ValidationError, "11 dígitos"):
			doc.insert()

	def test_denominacion_is_required(self):
		doc = self.make_transportista(denominacion="   ")

		with self.assertRaisesRegex(frappe.ValidationError, "denominación"):
			doc.insert()

	def test_document_identity_cannot_change_after_creation(self):
		doc = self.make_transportista().insert()
		doc.documento_numero = random_ruc()

		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden cambiar"):
			doc.save()
