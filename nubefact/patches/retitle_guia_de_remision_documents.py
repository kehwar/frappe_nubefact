from __future__ import annotations

import frappe

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision import (
	make_gre_title,
)

DOCTYPE = "Nubefact Guia De Remision"


def execute() -> None:
	"""Set the canonical title on existing GREs without changing their document names."""

	if not frappe.db.table_exists(DOCTYPE):
		return

	rows = frappe.get_all(
		DOCTYPE,
		filters={"numero": [">", 0]},
		fields=["name", "company", "tipo_de_comprobante", "serie", "numero", "title"],
	)
	for row in rows:
		title = make_gre_title(
			row.company,
			row.tipo_de_comprobante,
			row.serie,
			row.numero,
			require_complete=False,
		)
		if title and row.title != title:
			frappe.db.set_value(DOCTYPE, row.name, "title", title, update_modified=False)
