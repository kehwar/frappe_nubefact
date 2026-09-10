# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from nubefact.nubefact.doctype.nubefact_api_log.nubefact_api_log import create_api_log


class TestNubefactAPILog(FrappeTestCase):
	def test_logs_are_server_created_and_immutable(self):
		forged_log = frappe.get_doc(
			{
				"doctype": "Nubefact API Log",
				"operacion": "generar_guia",
				"request_timestamp": now_datetime(),
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "sólo pueden ser creados por el servidor"):
			forged_log.insert(ignore_permissions=True)

		log_name = create_api_log(
			"generar_guia",
			None,
			"https://api.example.test/gre",
			None,
			None,
			now_datetime(),
			{"operacion": "generar_guia", "numero": 1},
			now_datetime(),
			200,
			{"codigo": 23},
			"Error",
			"23",
			"Este documento ya existe en NubeFact",
			1,
		)
		log = frappe.get_doc("Nubefact API Log", log_name)
		log.error_code = ""
		with self.assertRaisesRegex(frappe.ValidationError, "inmutables"):
			log.save(ignore_permissions=True)
		log.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "no se pueden eliminar"):
			log.delete(ignore_permissions=True)
