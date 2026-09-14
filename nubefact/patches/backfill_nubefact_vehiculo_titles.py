from __future__ import annotations

import frappe
from frappe.utils import cstr

DOCTYPE = "Nubefact Vehiculo"


def execute() -> None:
	"""Use the plate number as the title for existing vehicles with blank titles."""

	if not frappe.db.table_exists(DOCTYPE):
		return

	vehicles = frappe.get_all(DOCTYPE, fields=["name", "placa_numero", "title"])
	for vehicle in vehicles:
		if not cstr(vehicle.title).strip():
			frappe.db.set_value(
				DOCTYPE,
				vehicle.name,
				"title",
				vehicle.placa_numero,
				update_modified=False,
			)
