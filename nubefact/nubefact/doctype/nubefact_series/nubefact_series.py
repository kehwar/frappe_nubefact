# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, cint, cstr, get_datetime, now_datetime

DOCTYPE_BY_DOCUMENT_TYPE = {
	"1": "Nubefact Facturacion",
	"2": "Nubefact Facturacion",
	"3": "Nubefact Facturacion",
	"4": "Nubefact Facturacion",
	"7": "Nubefact Guia De Remision",
	"8": "Nubefact Guia De Remision",
}
SERIES_PREFIXES_BY_DOCUMENT_TYPE = {
	"1": "F",
	"2": "B",
	"3": "FB",
	"4": "FB",
	"7": "T",
	"8": "V",
}
# NubeFact uses provider-specific document type codes; titles use SUNAT Catálogo 01 codes.
SUNAT_DOCUMENT_TYPE_BY_NUBEFACT_TYPE = {
	"1": "01",  # Factura
	"2": "03",  # Boleta de venta
	"3": "07",  # Nota de crédito
	"4": "08",  # Nota de débito
	"7": "09",  # Guía de remisión remitente
	"8": "31",  # Guía de remisión transportista
}
SUPPORTED_DOCTYPES = set(DOCTYPE_BY_DOCUMENT_TYPE.values())
ISSUABLE_STATUSES = {"Borrador", "Error"}
MAX_DOCUMENT_NUMBER = 99_999_999


def compose_series_title(company: str, nubefact_document_type: str, series: str) -> str:
	company_abbr = cstr(frappe.get_cached_value("Company", company, "abbr")).strip()
	sunat_document_type = SUNAT_DOCUMENT_TYPE_BY_NUBEFACT_TYPE[cstr(nubefact_document_type).strip()]
	return f"{company_abbr}-{sunat_document_type}-{cstr(series).strip().upper()}"


class NubefactSeries(Document):
	"""Concurrency-safe next number for a NubeFact document series.

	``numero`` is the next value to issue, rather than the last value issued. This
	lets an administrator enter the desired initial number directly.
	"""

	def before_insert(self):
		self._normalize_values()
		if self.tipo_de_comprobante in SUNAT_DOCUMENT_TYPE_BY_NUBEFACT_TYPE:
			self.title = compose_series_title(self.company, self.tipo_de_comprobante, self.serie)

	def autoname(self):
		self.name = cstr(self.title).strip()

	def validate(self):
		self._normalize_values()
		self._validate_values()
		self._validate_key_is_immutable()
		self._validate_next_number_cannot_reuse_an_issued_number()

	def _normalize_values(self):
		self.company = cstr(self.company).strip()
		self.local = cstr(self.local).strip()
		self.tipo_de_comprobante = cstr(self.tipo_de_comprobante).strip()
		self.serie = cstr(self.serie).strip().upper()

	def _validate_values(self):
		if self.tipo_de_comprobante not in DOCTYPE_BY_DOCUMENT_TYPE:
			frappe.throw("El tipo de comprobante SUNAT/NubeFact no es compatible.")

		if not 1 <= cint(self.numero) <= MAX_DOCUMENT_NUMBER + 1:
			frappe.throw("El próximo número debe ser un entero válido.")

		expected_prefixes = SERIES_PREFIXES_BY_DOCUMENT_TYPE[self.tipo_de_comprobante]
		if not re.fullmatch(rf"[{expected_prefixes}][A-Z0-9]{{3}}", self.serie):
			frappe.throw(f"La serie no corresponde al tipo de comprobante {self.tipo_de_comprobante}.")

		local_company = frappe.db.get_value("Nubefact Local", self.local, "company")
		if local_company != self.company:
			frappe.throw("La compañía de la serie debe coincidir con la compañía del local.")

		if self.is_new() and frappe.db.exists(self.doctype, self.name):
			frappe.throw("Ya existe una Serie NubeFact para esta compañía, tipo de comprobante y serie.")

		duplicate = frappe.db.exists(
			"Nubefact Series",
			{
				"company": self.company,
				"tipo_de_comprobante": self.tipo_de_comprobante,
				"serie": self.serie,
				"name": ["!=", self.name or ""],
			},
		)
		if duplicate:
			frappe.throw("Ya existe una Serie NubeFact para esta compañía, tipo de comprobante y serie.")

	def _validate_key_is_immutable(self):
		if self.is_new():
			return

		stored = frappe.db.get_value(
			self.doctype,
			self.name,
			[
				"company",
				"local",
				"tipo_de_comprobante",
				"serie",
				"ultimo_numero_asignado",
			],
			as_dict=True,
		)
		if stored and any(
			cstr(stored.get(fieldname)) != cstr(self.get(fieldname))
			for fieldname in ("company", "local", "tipo_de_comprobante", "serie")
		):
			frappe.throw(
				"Compañía, local, tipo de comprobante y serie no pueden cambiarse después de crear la Serie NubeFact."
			)
		if stored and cint(stored.ultimo_numero_asignado) != cint(self.ultimo_numero_asignado):
			frappe.throw("El último número asignado es administrado automáticamente.")

	def _validate_next_number_cannot_reuse_an_issued_number(self):
		if cint(self.numero) <= cint(self.ultimo_numero_asignado):
			frappe.throw("El próximo número debe ser mayor que el último número asignado.")


def validate_document_is_not_being_issued(document: Document) -> None:
	"""Reject saves racing with an external issuance request."""

	if document.is_new():
		return

	table = f"tab{document.doctype}"
	rows = frappe.db.sql(
		f"SELECT `status` FROM `{table}` WHERE `name` = %s FOR UPDATE",  # nosec B608
		(document.name,),
	)
	if rows and rows[0][0] == "Enviando":
		frappe.throw("El documento está siendo emitido en NubeFact y no puede modificarse.")


def apply_and_validate_document_series(document: Document) -> None:
	"""Fill blank identity fields and validate them against the selected tracker."""

	series_name = cstr(document.get("nubefact_series")).strip()
	if not series_name:
		return

	tracker = frappe.db.get_value(
		"Nubefact Series",
		series_name,
		["company", "local", "tipo_de_comprobante", "serie"],
		as_dict=True,
	)
	if not tracker:
		frappe.throw("La Serie NubeFact seleccionada no existe.")

	for fieldname in ("company", "local", "tipo_de_comprobante", "serie"):
		expected = cstr(tracker.get(fieldname)).strip()
		actual = cstr(document.get(fieldname)).strip()
		if not actual:
			document.set(fieldname, expected)
		elif actual != expected:
			frappe.throw(
				f"{document.meta.get_label(fieldname)} no coincide con la Serie NubeFact seleccionada."
			)

	if DOCTYPE_BY_DOCUMENT_TYPE.get(tracker.tipo_de_comprobante) != document.doctype:
		frappe.throw("La Serie NubeFact seleccionada pertenece a otro tipo de documento.")

	_validate_document_local_company(document)
	_validate_assigned_document_identity_is_immutable(document)


def set_company_from_local(document: Document) -> None:
	"""Infer and validate a document company when no series has been selected yet."""

	local = cstr(document.get("local")).strip()
	if not local:
		return

	local_company = cstr(frappe.db.get_value("Nubefact Local", local, "company")).strip()
	company = cstr(document.get("company")).strip()
	if not company and local_company:
		document.company = local_company
	elif company != local_company:
		frappe.throw("La compañía del documento debe coincidir con la compañía del local.")


def allocate_document_number(document: Document, *, mark_as_issuing: bool = False) -> int:
	"""Atomically assign the selected tracker's next number to a persisted document.

	When ``mark_as_issuing`` is set, the document row is transitioned to
	``Enviando`` in the same transaction. This prevents two requests from issuing
	the same document after the row lock is released.
	"""

	series_name = cstr(document.get("nubefact_series")).strip()
	if not series_name:
		frappe.throw("Seleccione una Serie NubeFact antes de emitir el documento.")
	if document.doctype not in SUPPORTED_DOCTYPES or document.is_new():
		frappe.throw("El documento debe estar guardado antes de asignar su número.")

	table = f"tab{document.doctype}"
	current_rows = frappe.db.sql(
		f"""
		SELECT `status`, `numero`, `numero_asignado_automaticamente`, `nubefact_series`
		FROM `{table}`
		WHERE `name` = %s
		FOR UPDATE
		""",  # nosec B608
		(document.name,),
		as_dict=True,
	)
	if not current_rows:
		frappe.throw("No se encontró el documento que se desea numerar.")

	current = current_rows[0]
	if current.nubefact_series != series_name:
		frappe.throw("La Serie NubeFact del documento cambió; vuelva a cargarlo.")
	if mark_as_issuing and current.status not in ISSUABLE_STATUSES:
		frappe.throw("El documento ya está siendo emitido o ya fue enviado a NubeFact.")

	tracker_rows: list[dict[str, Any]] = frappe.db.sql(
		"""
		SELECT `company`, `local`, `tipo_de_comprobante`, `serie`, `numero`, `ultimo_numero_asignado`
		FROM `tabNubefact Series`
		WHERE `name` = %s
		FOR UPDATE
		""",
		(series_name,),
		as_dict=True,
	)
	if not tracker_rows:
		frappe.throw("La Serie NubeFact seleccionada no existe.")

	tracker = tracker_rows[0]
	_apply_locked_tracker_values(document, tracker)

	stored_number = cint(current.numero)
	if cint(current.numero_asignado_automaticamente):
		number = stored_number
		if not 1 <= number <= MAX_DOCUMENT_NUMBER:
			frappe.throw("El documento no tiene un número automático válido.")
	else:
		# Preserve numbers from imports or existing manual documents. Empty drafts
		# receive the configured next number.
		number = stored_number or cint(tracker.numero)
		if not 1 <= number <= MAX_DOCUMENT_NUMBER:
			frappe.throw("La Serie NubeFact no tiene un próximo número válido.")

		if _number_belongs_to_another_document(document, number):
			frappe.throw(
				"El número de la Serie NubeFact ya está asignado a otro documento. "
				"Corrija el próximo número antes de emitir."
			)

		next_number = max(cint(tracker.numero), number + 1)
		frappe.db.set_value(
			"Nubefact Series",
			series_name,
			{
				"numero": next_number,
				"ultimo_numero_asignado": max(number, cint(tracker.get("ultimo_numero_asignado"))),
			},
			update_modified=True,
		)

	document.numero = number
	document.numero_asignado_automaticamente = 1
	document.title = document._compose_title()
	values: dict[str, Any] = {
		"numero": number,
		"numero_asignado_automaticamente": 1,
		"title": document.title,
	}
	if mark_as_issuing:
		document.status = "Enviando"
		values["status"] = "Enviando"
	frappe.db.set_value(document.doctype, document.name, values, update_modified=True)
	return number


def advance_document_number_after_nubefact_duplicate(
	document: Document, *, expected_number: int, expected_modified: Any
) -> int:
	"""Replace a freshly reserved number that NubeFact reports as already existing.

	The caller must commit the replacement before retrying the external request.
	The expected number and ``Enviando`` state prevent a stale request from
	renumbering a document owned by a newer issuance attempt.
	"""

	if document.doctype not in SUPPORTED_DOCTYPES or document.is_new():
		frappe.throw("El documento debe estar guardado antes de reemplazar su número.")

	expected_number = cint(expected_number)
	current = _lock_current_document_issuance(document, expected_modified)
	if not cint(current.numero_asignado_automaticamente):
		frappe.throw("Solo se puede reemplazar un número reservado automáticamente.")
	if cint(current.numero) != expected_number:
		frappe.throw("El número del documento cambió durante el envío; vuelva a cargarlo.")
	if cstr(current.nubefact_series).strip() != cstr(document.nubefact_series).strip():
		frappe.throw("La Serie NubeFact del documento cambió; vuelva a cargarlo.")

	series_name = cstr(current.nubefact_series).strip()
	tracker_rows: list[dict[str, Any]] = frappe.db.sql(
		"""
		SELECT `company`, `local`, `tipo_de_comprobante`, `serie`, `numero`, `ultimo_numero_asignado`
		FROM `tabNubefact Series`
		WHERE `name` = %s
		FOR UPDATE
		""",
		(series_name,),
		as_dict=True,
	)
	if not tracker_rows:
		frappe.throw("La Serie NubeFact seleccionada no existe.")

	tracker = tracker_rows[0]
	_apply_locked_tracker_values(document, tracker)
	new_number = max(cint(tracker.numero), expected_number + 1)
	while new_number <= MAX_DOCUMENT_NUMBER and _number_belongs_to_another_document(
		document, new_number
	):
		new_number += 1
	if new_number > MAX_DOCUMENT_NUMBER:
		frappe.throw("La Serie NubeFact no tiene más números válidos disponibles.")

	frappe.db.set_value(
		"Nubefact Series",
		series_name,
		{
			"numero": new_number + 1,
			"ultimo_numero_asignado": max(
				new_number, cint(tracker.get("ultimo_numero_asignado"))
			),
		},
		update_modified=True,
	)

	document.numero = new_number
	document.numero_asignado_automaticamente = 1
	document.title = document._compose_title()
	frappe.db.set_value(
		document.doctype,
		document.name,
		{
			"numero": new_number,
			"numero_asignado_automaticamente": 1,
			"title": document.title,
		},
		# Preserve the issuance lease in ``modified``. Stale recovery or a newer
		# issuance changes it and prevents this worker from renumbering the document.
		update_modified=False,
	)
	return new_number


def validate_document_issuance_lease(document: Document, expected_modified: Any) -> None:
	"""Lock the document and reject responses from an obsolete issuance worker."""

	_lock_current_document_issuance(document, expected_modified)


def _lock_current_document_issuance(document: Document, expected_modified: Any) -> dict[str, Any]:
	if document.doctype not in SUPPORTED_DOCTYPES or document.is_new():
		frappe.throw("El documento debe estar guardado antes de validar su envío.")

	table = f"tab{document.doctype}"
	current_rows = frappe.db.sql(
		f"""
		SELECT `status`, `numero`, `numero_asignado_automaticamente`, `nubefact_series`, `modified`
		FROM `{table}`
		WHERE `name` = %s
		FOR UPDATE
		""",  # nosec B608
		(document.name,),
		as_dict=True,
	)
	if not current_rows:
		frappe.throw("No se encontró el documento que se está emitiendo.")

	current = current_rows[0]
	if current.status != "Enviando" or get_datetime(current.modified) != get_datetime(
		expected_modified
	):
		frappe.throw("El documento ya no pertenece a este intento de envío.")
	return current


def _number_belongs_to_another_document(document: Document, number: int) -> bool:
	identity = {
		"tipo_de_comprobante": document.tipo_de_comprobante,
		"serie": document.serie,
		"numero": number,
		"name": ["!=", document.name],
	}
	return bool(
		frappe.db.exists(document.doctype, {**identity, "company": document.company})
		or frappe.db.exists(document.doctype, {**identity, "local": document.local})
	)


def _apply_locked_tracker_values(document: Document, tracker: dict[str, Any]) -> None:
	for fieldname in ("company", "local", "tipo_de_comprobante", "serie"):
		if cstr(document.get(fieldname)).strip() != cstr(tracker.get(fieldname)).strip():
			frappe.throw(
				f"{document.meta.get_label(fieldname)} no coincide con la Serie NubeFact seleccionada."
			)
	if DOCTYPE_BY_DOCUMENT_TYPE.get(tracker.tipo_de_comprobante) != document.doctype:
		frappe.throw("La Serie NubeFact seleccionada pertenece a otro tipo de documento.")
	_validate_document_local_company(document)


def _validate_document_local_company(document: Document) -> None:
	local = cstr(document.get("local")).strip()
	company = cstr(document.get("company")).strip()
	local_company = cstr(frappe.db.get_value("Nubefact Local", local, "company")).strip()
	if not local or not company or local_company != company:
		frappe.throw("El local y la compañía del documento deben coincidir con la Serie NubeFact.")


def recover_stale_issuing_documents() -> None:
	"""Make reservations retryable if a worker died after committing them."""

	cutoff = add_to_date(now_datetime(), minutes=-10)
	for doctype in SUPPORTED_DOCTYPES:
		stale_names = frappe.get_all(
			doctype,
			filters={"status": "Enviando", "modified": ["<", cutoff]},
			pluck="name",
			limit=100,
		)
		table = f"tab{doctype}"
		for name in stale_names:
			# The initial query is only a snapshot. Recheck both values in the
			# update so this job cannot overwrite a newer issuance attempt.
			frappe.db.sql(
				f"""
				UPDATE `{table}`
				SET `status` = %s, `error_message` = %s, `modified` = %s
				WHERE `name` = %s AND `status` = %s AND `modified` < %s
				""",  # nosec B608
				(
					"Error",
					"El envío no terminó correctamente. Puede reintentar con el mismo número reservado.",
					now_datetime(),
					name,
					"Enviando",
					cutoff,
				),
			)


def _validate_assigned_document_identity_is_immutable(document: Document) -> None:
	if document.is_new() or not cint(document.get("numero_asignado_automaticamente")):
		return

	stored = frappe.db.get_value(
		document.doctype,
		document.name,
		["company", "local", "nubefact_series", "tipo_de_comprobante", "serie", "numero"],
		as_dict=True,
	)
	if stored and any(
		cstr(stored.get(fieldname)) != cstr(document.get(fieldname))
		for fieldname in (
			"company",
			"local",
			"nubefact_series",
			"tipo_de_comprobante",
			"serie",
			"numero",
		)
	):
		frappe.throw(
			"La compañía, el local, el tipo de comprobante, la serie y el número no pueden cambiar después de asignar el número."
		)
