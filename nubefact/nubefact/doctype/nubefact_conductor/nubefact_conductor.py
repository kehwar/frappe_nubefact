# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr


class NubefactConductor(Document):
	def before_validate(self):
		self.documento_tipo = cstr(self.documento_tipo).strip()
		self.documento_numero = cstr(self.documento_numero).strip().upper()
		self.numero_licencia = cstr(self.numero_licencia).strip().upper()
		self.nombre = cstr(self.nombre).strip()
		self.apellidos = cstr(self.apellidos).strip()
		self.denominacion = cstr(self.denominacion).strip()
		self.nombre_completo = " ".join(value for value in (self.nombre, self.apellidos) if value)

	def autoname(self):
		self.before_validate()
		self.name = f"{self.documento_tipo}-{self.documento_numero}"

	def validate(self):
		if not cint(
			frappe.db.get_value("Nubefact Tipo de Documento", self.documento_tipo, "aplica_conductor")
		):
			frappe.throw("El tipo de documento no pertenece al catálogo de conductores de NubeFact.")
		if not 1 <= len(self.documento_numero) <= 15:
			frappe.throw("El número de documento debe tener entre 1 y 15 caracteres.")
		if not self.nombre or len(self.nombre) > 250:
			frappe.throw("El nombre debe tener entre 1 y 250 caracteres.")
		if not self.apellidos or len(self.apellidos) > 250:
			frappe.throw("Los apellidos deben tener entre 1 y 250 caracteres.")
		if len(self.denominacion) > 100:
			frappe.throw("La denominación no puede tener más de 100 caracteres.")
		if not re.fullmatch(r"[A-Z0-9]{9,10}", self.numero_licencia):
			frappe.throw("El número de licencia debe tener 9 a 10 mayúsculas o números.")
		if not self.is_new() and self.name != f"{self.documento_tipo}-{self.documento_numero}":
			frappe.throw(
				"El tipo y el número de documento no se pueden cambiar después de crear el conductor."
			)
