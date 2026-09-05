# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import cstr


class NubefactCatalogDocument(Document):
	"""Base controller for code-backed NubeFact master data."""

	def before_validate(self):
		self.codigo = cstr(self.codigo).strip()
		self.descripcion = cstr(self.descripcion).strip()

	def autoname(self):
		self.name = self.codigo

	def validate(self):
		if not self.codigo:
			frappe.throw("El código es obligatorio.")
		if not self.descripcion:
			frappe.throw("La descripción es obligatoria.")
		if not self.is_new() and self.name != self.codigo:
			frappe.throw("El código no se puede cambiar después de crear el registro.")
