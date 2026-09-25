from __future__ import annotations

import frappe

DOCTYPE = "Nubefact Guia De Remision"


def execute() -> None:
	"""Classify existing manual void requests without losing their original details."""

	if not frappe.db.table_exists(DOCTYPE) or not frappe.db.has_column(DOCTYPE, "momento_de_anulacion"):
		return

	# Older requests did not record when the void happened. Treat those as
	# before departure, including requests later reversed back to Aceptada.
	frappe.db.sql(
		"""
		UPDATE `tabNubefact Guia De Remision`
		SET `momento_de_anulacion` = 'Antes de iniciar el traslado'
		WHERE (`momento_de_anulacion` IS NULL OR `momento_de_anulacion` = '')
			AND (
				`fecha_de_solicitud_de_anulacion` IS NOT NULL
				OR `status` IN ('Anulación Solicitada', 'Anulada')
			)
		"""
	)
