# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cstr

DEFAULT_BASE_URL = "https://api.nubefact.com/api/v1"


class NubefactLocal(Document):
	def before_validate(self):
		self._set_ubigeo_location()

	def autoname(self):
		title = cstr(self.title).strip()
		company_abbr = cstr(frappe.db.get_value("Company", self.company, "abbr")).strip()
		self.name = append_number_if_name_exists("Nubefact Local", f"{title}-{company_abbr}")

	def _set_ubigeo_location(self):
		if not self.ubigeo:
			self.departamento = None
			self.provincia = None
			self.distrito = None
			return

		location = frappe.db.get_value(
			"Nubefact Ubigeo",
			self.ubigeo,
			["departamento", "provincia", "distrito"],
			as_dict=True,
		)
		if not location:
			frappe.throw("El UBIGEO seleccionado no existe en el catálogo INEI.")

		self.update(location)


def sync_local_ubigeos() -> int:
	"""Refresh stored location names for existing locals with a valid UBIGEO."""
	locals_with_ubigeo = frappe.get_all(
		"Nubefact Local",
		filters={"ubigeo": ["is", "set"]},
		fields=["name", "ubigeo", "departamento", "provincia", "distrito"],
	)
	if not locals_with_ubigeo:
		return 0

	locations = {
		record.name: record
		for record in frappe.get_all(
			"Nubefact Ubigeo",
			filters={"name": ["in", list({record.ubigeo for record in locals_with_ubigeo})]},
			fields=["name", "departamento", "provincia", "distrito"],
		)
	}
	updates = {}
	unknown_ubigeos = set()
	for local in locals_with_ubigeo:
		location = locations.get(local.ubigeo)
		if not location:
			unknown_ubigeos.add(local.ubigeo)
			continue
		values = {
			"departamento": location.departamento,
			"provincia": location.provincia,
			"distrito": location.distrito,
		}
		if any(cstr(local.get(fieldname)).strip() != value for fieldname, value in values.items()):
			updates[local.name] = values

	if updates:
		frappe.db.bulk_update("Nubefact Local", updates)
	if unknown_ubigeos:
		frappe.logger("nubefact").warning(
			"Existing Nubefact Local records reference unknown UBIGEO values: %s",
			", ".join(sorted(unknown_ubigeos)),
		)
	return len(updates)


def get_origin_values(local: str | None) -> dict[str, str | None]:
	local_doc = frappe.get_doc("Nubefact Local", local) if local else None

	local_origin_ubigeo = cstr(local_doc.ubigeo).strip() if local_doc else None
	local_origin_address = cstr(local_doc.direccion).strip() if local_doc else None
	local_origin_sunat_code = cstr(local_doc.codigo_sunat).strip() if local_doc else None

	return {
		"punto_de_partida_ubigeo": local_origin_ubigeo,
		"punto_de_partida_direccion": local_origin_address,
		"punto_de_partida_codigo_establecimiento_sunat": local_origin_sunat_code,
	}


def get_last_used_local_for_user(
	*, doctype: str, user: str | None = None, exclude_name: str | None = None
) -> str | None:
	if not cstr(doctype).strip():
		frappe.throw("Se requiere DocType.")

	if doctype not in ("Nubefact Guia De Remision", "Nubefact Facturacion"):
		frappe.throw(
			"DocType no soportado. Se esperaba 'Nubefact Guia De Remision' o 'Nubefact Facturacion'."
		)

	filters = {
		"owner": cstr(user or frappe.session.user).strip(),
		"local": ["is", "set"],
	}

	if exclude_name:
		filters["name"] = ["!=", exclude_name]

	last_local = frappe.get_all(
		doctype,
		filters=filters,
		pluck="local",
		order_by="modified desc",
		limit=1,
	)

	return last_local[0] if last_local else None


def _build_request_url(route: str | None) -> str:
	if not route:
		frappe.throw("Nubefact Local Route is required.")

	clean_route = route.strip()
	if clean_route.startswith("http://") or clean_route.startswith("https://"):
		return clean_route

	return f"{DEFAULT_BASE_URL}/{clean_route.lstrip('/')}"


def get_request_config(local: str) -> tuple[Document, str, str]:
	local_doc = frappe.get_doc("Nubefact Local", local)
	url = _build_request_url(local_doc.ruta_api)
	token = local_doc.get_password("token_api")
	if not token:
		frappe.throw("Nubefact Local Token is required.")

	return local_doc, url, token
