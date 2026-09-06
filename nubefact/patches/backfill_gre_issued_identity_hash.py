from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import cint, cstr

from nubefact.nubefact.doctype.nubefact_series.nubefact_series import (
	make_issued_identity_hash,
)

DOCTYPE = "Nubefact Guia De Remision"
TABLE = "tabNubefact Guia De Remision"


def execute() -> None:
	"""Create and backfill the race guard before DocType unique-index synchronization."""

	if not frappe.db.table_exists(DOCTYPE):
		return
	if not frappe.db.has_column(DOCTYPE, "issued_identity_hash"):
		frappe.db.sql(f"ALTER TABLE `{TABLE}` ADD COLUMN `issued_identity_hash` varchar(64) NULL")

	rows = frappe.db.sql(
		f"""
		SELECT `name`, `company`, `tipo_de_comprobante`, `serie`, `numero`
		FROM `{TABLE}`
		WHERE `numero_asignado_automaticamente` = 1
			AND `numero` IS NOT NULL AND `numero` > 0
		""",  # nosec B608
		as_dict=True,
	)
	identities: dict[tuple[str, str, str, int], list[str]] = defaultdict(list)
	for row in rows:
		identity = (
			cstr(row.company or "").strip(),
			cstr(row.tipo_de_comprobante or "").strip(),
			cstr(row.serie or "").strip().upper(),
			cint(row.numero),
		)
		identities[identity].append(row.name)

	duplicates = {identity: names for identity, names in identities.items() if len(names) > 1}
	if duplicates:
		report = "; ".join(
			f"{company}/{document_type}/{series}/{number}: {', '.join(names)}"
			for (company, document_type, series, number), names in sorted(duplicates.items())
		)
		frappe.throw(
			"No se puede crear la restricción de identidad emitida. "
			f"Corrija estas GRE duplicadas y vuelva a ejecutar la migración: {report}"
		)

	for (company, document_type, series, number), names in identities.items():
		identity_hash = make_issued_identity_hash(company, document_type, series, number)
		frappe.db.set_value(
			DOCTYPE,
			names[0],
			"issued_identity_hash",
			identity_hash,
			update_modified=False,
		)
