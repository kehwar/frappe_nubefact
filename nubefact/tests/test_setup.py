import frappe
from frappe.tests.utils import FrappeTestCase

from nubefact import hooks
from nubefact.setup import ROLES, setup

WRITE_DOCTYPES = {
	"Nubefact Facturacion",
	"Nubefact Guia De Remision",
}
READ_ONLY_DOCTYPES = {
	"Nubefact API Log",
	"Nubefact Local",
	"Nubefact Series",
}


class TestSetup(FrappeTestCase):
	def test_setup_is_registered_for_install_and_migrate(self):
		self.assertEqual(hooks.after_install, "nubefact.setup.setup")
		self.assertEqual(hooks.after_migrate, "nubefact.setup.setup")

	def test_setup_is_idempotent(self):
		setup()
		setup()

		for role_name in ROLES:
			self.assertEqual(frappe.db.count("Role", {"name": role_name}), 1)
			role = frappe.get_doc("Role", role_name)
			self.assertFalse(role.disabled)
			self.assertTrue(role.desk_access)

	def test_managers_have_write_access_to_all_nubefact_doctypes(self):
		for doctype in WRITE_DOCTYPES | READ_ONLY_DOCTYPES:
			for role in ("System Manager", "Nubefact Manager"):
				permission = self._get_permission(doctype, role)
				self.assertTrue(permission.read)
				self.assertTrue(permission.write)
				self.assertTrue(permission.create)
				self.assertTrue(permission.delete)

	def test_accounts_manager_has_no_nubefact_permissions(self):
		permissions = frappe.get_all(
			"DocPerm",
			filters={
				"parent": ["in", sorted(WRITE_DOCTYPES | READ_ONLY_DOCTYPES)],
				"role": "Accounts Manager",
			},
		)
		self.assertFalse(permissions)

	def test_user_permission_matrix(self):
		for doctype in WRITE_DOCTYPES:
			permission = self._get_permission(doctype, "Nubefact User")
			self.assertTrue(permission.read)
			self.assertTrue(permission.write)
			self.assertTrue(permission.create)
			self.assertTrue(permission.delete)

		for doctype in READ_ONLY_DOCTYPES:
			permission = self._get_permission(doctype, "Nubefact User")
			self.assertTrue(permission.read)
			self.assertFalse(permission.write)
			self.assertFalse(permission.create)
			self.assertFalse(permission.delete)

	def _get_permission(self, doctype, role):
		permission = frappe.db.get_value(
			"DocPerm",
			{"parent": doctype, "role": role, "permlevel": 0},
			["read", "write", "create", "delete"],
			as_dict=True,
		)
		self.assertIsNotNone(permission, f"Missing {role} permission for {doctype}")
		return permission
