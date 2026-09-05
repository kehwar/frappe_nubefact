import frappe
from frappe.tests.utils import FrappeTestCase

from nubefact import hooks
from nubefact.master_data import MASTER_DATA
from nubefact.setup import ROLES, setup

WRITE_DOCTYPES = {
	"Nubefact Facturacion",
	"Nubefact Guia De Remision",
}
READ_ONLY_DOCTYPES = {
	"Nubefact API Log",
	"Nubefact Local",
	"Nubefact Series",
	"Nubefact Ubigeo",
	*MASTER_DATA,
}

CATALOG_LINK_FIELDS = {
	"Nubefact Facturacion": {
		"tipo_de_comprobante": "Nubefact Tipo de Comprobante",
		"cliente_tipo_de_documento": "Nubefact Tipo de Documento",
	},
	"Nubefact Facturacion Item": {"unidad_de_medida": "Nubefact Unidad de Medida"},
	"Nubefact Guia De Remision": {
		"tipo_de_comprobante": "Nubefact Tipo de Comprobante",
		"cliente_tipo_de_documento": "Nubefact Tipo de Documento",
		"destinatario_documento_tipo": "Nubefact Tipo de Documento",
		"motivo_de_traslado": "Nubefact Motivo de Traslado",
		"documento_relacionado_codigo": "Nubefact Codigo de Documento Relacionado",
		"tipo_de_transporte": "Nubefact Tipo de Transporte",
		"peso_bruto_unidad_de_medida": "Nubefact Unidad de Medida",
		"transportista_documento_tipo": "Nubefact Tipo de Documento",
		"conductor_documento_tipo": "Nubefact Tipo de Documento",
		"sunat_envio_indicador": "Nubefact Indicador Sunat",
		"subcontratador_documento_tipo": "Nubefact Tipo de Documento",
		"pagador_servicio_documento_tipo_identidad": "Nubefact Tipo de Documento",
	},
	"Nubefact Guia De Remision Conductor Secundario": {"documento_tipo": "Nubefact Tipo de Documento"},
	"Nubefact Guia De Remision Documento Relacionado": {"tipo": "Nubefact Tipo de Documento Relacionado"},
	"Nubefact Guia De Remision Item": {"unidad_de_medida": "Nubefact Unidad de Medida"},
	"Nubefact Series": {"tipo_de_comprobante": "Nubefact Tipo de Comprobante"},
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

		for doctype, records in MASTER_DATA.items():
			for record in records:
				self.assertEqual(frappe.db.count(doctype, {"name": record["codigo"]}), 1)

	def test_setup_populates_master_data(self):
		setup()

		for doctype, records in MASTER_DATA.items():
			expected = {record["codigo"]: record for record in records}
			installed = {
				record.name: record
				for record in frappe.get_all(
					doctype,
					filters={"name": ["in", list(expected)]},
					fields=["name", *next(iter(expected.values()))],
				)
			}
			self.assertEqual(set(installed), set(expected))
			for code, values in expected.items():
				for fieldname, value in values.items():
					self.assertEqual(installed[code].get(fieldname), value)

	def test_setup_preserves_and_normalizes_existing_item_units(self):
		row = frappe.get_doc(
			{
				"doctype": "Nubefact Facturacion Item",
				"parent": "legacy-unit-test",
				"parenttype": "Nubefact Facturacion",
				"parentfield": "items",
				"idx": 1,
				"unidad_de_medida": " X9ZQ ",
			}
		)
		row.db_insert()

		setup()

		self.assertEqual(
			frappe.db.get_value(row.doctype, row.name, "unidad_de_medida"),
			"X9ZQ",
		)
		self.assertEqual(
			frappe.db.get_value("Nubefact Unidad de Medida", "X9ZQ", "descripcion"),
			"Unidad de medida existente",
		)

	def test_opaque_code_fields_are_links_to_master_data(self):
		for doctype, fields in CATALOG_LINK_FIELDS.items():
			meta = frappe.get_meta(doctype)
			for fieldname, options in fields.items():
				field = meta.get_field(fieldname)
				self.assertEqual(field.fieldtype, "Link")
				self.assertEqual(field.options, options)

	def test_workspace_links_every_standalone_nubefact_doctype(self):
		expected = set(
			frappe.get_all(
				"DocType",
				filters={"module": "Nubefact", "istable": 0},
				pluck="name",
			)
		)
		workspace = frappe.get_doc("Workspace", "Nubefact")
		linked = {
			link.link_to
			for link in workspace.links
			if link.type == "Link" and link.link_type == "DocType"
		}

		self.assertEqual(linked, expected)

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
