from __future__ import annotations

import frappe


def execute() -> None:
	if not frappe.db.table_exists("Nubefact Migration Job Item"):
		return
	frappe.db.add_unique(
		"Nubefact Migration Job Item",
		["parent", "number"],
		constraint_name="unique_migration_job_number",
	)
