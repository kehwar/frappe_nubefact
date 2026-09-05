import frappe

from nubefact.master_data import load_master_data
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import sync_local_ubigeos
from nubefact.nubefact.doctype.nubefact_ubigeo.nubefact_ubigeo import load_ubigeos

ROLES = ("Nubefact Manager", "Nubefact User")


def setup():
	"""Ensure Nubefact roles and bundled master data are installed."""
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": 1,
				}
			).insert(ignore_permissions=True)
			continue

		role = frappe.get_doc("Role", role_name)
		if role.disabled or not role.desk_access:
			role.disabled = 0
			role.desk_access = 1
			role.save(ignore_permissions=True)

	load_master_data()
	load_ubigeos()
	sync_local_ubigeos()
