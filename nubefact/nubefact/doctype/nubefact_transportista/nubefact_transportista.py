# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import cstr


class NubefactTransportista(Document):
	def before_validate(self):
		self.documento_tipo = cstr(self.documento_tipo).strip()
		self.documento_numero = cstr(self.documento_numero).strip().upper()
		self.denominacion = cstr(self.denominacion).strip()

	def autoname(self):
		self.before_validate()
		self.name = f"{self.documento_tipo}-{self.documento_numero}"

	def validate(self):
		if self.documento_tipo != "6":
			frappe.throw("El tipo de documento del transportista debe ser 6 (RUC).")
		if not re.fullmatch(r"\d{11}", self.documento_numero):
			frappe.throw("El RUC del transportista debe tener 11 dígitos.")
		if not self.denominacion or len(self.denominacion) > 100:
			frappe.throw("La denominación debe tener entre 1 y 100 caracteres.")
		if not self.is_new() and self.name != f"{self.documento_tipo}-{self.documento_numero}":
			frappe.throw(
				"El tipo y el número de documento no se pueden cambiar después de crear el transportista."
			)
