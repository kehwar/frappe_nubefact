# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import cstr


class NubefactVehiculo(Document):
	def before_validate(self):
		self.placa_numero = cstr(self.placa_numero).strip().upper()
		self.title = cstr(self.title).strip() or None

	def autoname(self):
		self.before_validate()
		self.name = self.placa_numero

	def validate(self):
		if not re.fullmatch(r"[A-Z0-9]{6,8}", self.placa_numero) or set(self.placa_numero) <= {"0"}:
			frappe.throw(
				"El número de placa debe tener 6 a 8 mayúsculas o números, sin guiones, y no puede ser cero."
			)
		if not self.is_new() and self.name != self.placa_numero:
			frappe.throw("El número de placa no se puede cambiar después de crear el vehículo.")
