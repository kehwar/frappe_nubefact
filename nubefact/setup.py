import frappe

ROLES = ("Nubefact Manager", "Nubefact User")


def setup():
	"""Ensure the roles managed by Nubefact are installed and enabled."""
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
