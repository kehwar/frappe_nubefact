import frappe

from nubefact.nubefact.doctype.nubefact_series.nubefact_series import (
	SUNAT_DOCUMENT_TYPE_BY_NUBEFACT_TYPE,
	compose_series_title,
)


def execute():
	series_records = frappe.get_all(
		"Nubefact Series",
		fields=["name", "company", "tipo_de_comprobante", "serie"],
	)
	for record in series_records:
		if record.tipo_de_comprobante not in SUNAT_DOCUMENT_TYPE_BY_NUBEFACT_TYPE:
			continue

		frappe.db.set_value(
			"Nubefact Series",
			record.name,
			"title",
			compose_series_title(record.company, record.tipo_de_comprobante, record.serie),
			update_modified=False,
		)
