# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import cstr, now_datetime

UBIGEO_DATA_FILE = Path(__file__).with_name("ubigeos_inei_2025.csv")
UBIGEO_DATA_SHA256 = "db880993966e4d947899faf2efe51912cc89896a481bd7f67c01215a81a40e64"
EXPECTED_UBIGEO_COUNT = 1892
UBIGEO_FIELDS = ("codigo", "departamento", "provincia", "distrito")
GRE_UBIGEO_FIELDS = ("punto_de_partida_ubigeo", "punto_de_llegada_ubigeo")


class NubefactUbigeo(Document):
	def before_validate(self):
		self.codigo = cstr(self.codigo).strip()
		for fieldname in ("departamento", "provincia", "distrito"):
			self.set(fieldname, cstr(self.get(fieldname)).strip().upper())
		self.title = format_ubigeo_title(
			self.codigo,
			self.departamento,
			self.provincia,
			self.distrito,
		)

	def autoname(self):
		self.name = self.codigo

	def validate(self):
		if not re.fullmatch(r"\d{6}", self.codigo):
			frappe.throw("El código UBIGEO debe contener exactamente 6 dígitos.")
		if not self.is_new() and self.name != self.codigo:
			frappe.throw("El código UBIGEO no se puede cambiar después de crear el registro.")

		canonical = {record["codigo"]: record for record in get_ubigeo_records()}.get(self.codigo)
		if not canonical:
			frappe.throw("El código no pertenece al catálogo UBIGEO INEI 2025.")
		if any(cstr(self.get(fieldname)).strip() != canonical[fieldname] for fieldname in UBIGEO_FIELDS):
			frappe.throw("Los datos del UBIGEO deben coincidir con el catálogo oficial INEI 2025.")


def format_ubigeo_title(codigo: str, departamento: str, provincia: str, distrito: str) -> str:
	return (
		f"{cstr(codigo).strip()} - {cstr(departamento).strip()} - "
		f"{cstr(provincia).strip()} - {cstr(distrito).strip()}"
	)


def get_ubigeo_records() -> list[dict[str, str]]:
	if hashlib.sha256(UBIGEO_DATA_FILE.read_bytes()).hexdigest() != UBIGEO_DATA_SHA256:
		frappe.throw("El archivo del catálogo UBIGEO no coincide con su checksum esperado.")

	with UBIGEO_DATA_FILE.open(encoding="utf-8", newline="") as source:
		reader = csv.DictReader(source)
		if tuple(reader.fieldnames or ()) != UBIGEO_FIELDS:
			frappe.throw("El catálogo UBIGEO no contiene las columnas esperadas.")
		records = [
			{
				"codigo": cstr(record["codigo"]).strip(),
				"departamento": cstr(record["departamento"]).strip().upper(),
				"provincia": cstr(record["provincia"]).strip().upper(),
				"distrito": cstr(record["distrito"]).strip().upper(),
			}
			for record in reader
		]

	codes = {record["codigo"] for record in records}
	if len(records) != EXPECTED_UBIGEO_COUNT or len(codes) != EXPECTED_UBIGEO_COUNT:
		frappe.throw(
			f"El catálogo UBIGEO debe contener {EXPECTED_UBIGEO_COUNT} distritos únicos; "
			f"se encontraron {len(records)} filas y {len(codes)} códigos."
		)
	if any(not re.fullmatch(r"\d{6}", code) for code in codes):
		frappe.throw("El catálogo UBIGEO contiene códigos que no tienen 6 dígitos.")
	if any(not cstr(record[fieldname]).strip() for record in records for fieldname in UBIGEO_FIELDS):
		frappe.throw("El catálogo UBIGEO contiene campos obligatorios vacíos.")

	return records


def load_ubigeos() -> int:
	"""Reconcile the installed master with the bundled INEI district catalog."""
	records = get_ubigeo_records()
	canonical_by_code = {record["codigo"]: record for record in records}
	existing = frappe.get_all("Nubefact Ubigeo", fields=["name", *UBIGEO_FIELDS, "title"])
	existing_by_name = {record.name: record for record in existing}

	conflicts = [
		record for record in existing if record.codigo in canonical_by_code and record.name != record.codigo
	]
	if conflicts:
		frappe.throw(
			"Hay registros Nubefact Ubigeo cuyo nombre no coincide con el código oficial: "
			+ ", ".join(record.name for record in conflicts[:10])
		)

	timestamp = now_datetime()
	updates = {}
	for code, canonical in canonical_by_code.items():
		current = existing_by_name.get(code)
		if not current:
			continue
		expected = {
			**canonical,
			"title": format_ubigeo_title(
				canonical["codigo"],
				canonical["departamento"],
				canonical["provincia"],
				canonical["distrito"],
			),
		}
		if any(cstr(current.get(fieldname)).strip() != value for fieldname, value in expected.items()):
			updates[code] = expected

	if updates:
		frappe.db.bulk_update(
			"Nubefact Ubigeo",
			updates,
			modified=timestamp,
			modified_by="Administrator",
		)

	missing_records = [record for record in records if record["codigo"] not in existing_by_name]
	if missing_records:
		frappe.db.bulk_insert(
			"Nubefact Ubigeo",
			fields=[
				"name",
				"creation",
				"modified",
				"modified_by",
				"owner",
				"docstatus",
				"idx",
				*UBIGEO_FIELDS,
				"title",
			],
			values=(
				(
					record["codigo"],
					timestamp,
					timestamp,
					"Administrator",
					"Administrator",
					0,
					0,
					*(record[fieldname] for fieldname in UBIGEO_FIELDS),
					format_ubigeo_title(
						record["codigo"],
						record["departamento"],
						record["provincia"],
						record["distrito"],
					),
				)
				for record in missing_records
			),
		)

	_verify_installed_catalog(canonical_by_code)
	_warn_about_unknown_gre_ubigeos(set(canonical_by_code))
	return len(missing_records)


def _verify_installed_catalog(canonical_by_code: dict[str, dict[str, str]]) -> None:
	installed = frappe.get_all(
		"Nubefact Ubigeo",
		filters={"name": ["in", list(canonical_by_code)]},
		fields=["name", *UBIGEO_FIELDS],
	)
	installed_by_name = {record.name: record for record in installed}
	invalid_codes = [
		code
		for code, canonical in canonical_by_code.items()
		if code not in installed_by_name
		or any(
			cstr(installed_by_name[code].get(fieldname)).strip() != canonical[fieldname]
			for fieldname in UBIGEO_FIELDS
		)
	]
	if invalid_codes:
		frappe.throw(
			"No se pudo instalar correctamente el catálogo UBIGEO INEI: " + ", ".join(invalid_codes[:10])
		)


def _warn_about_unknown_gre_ubigeos(canonical_codes: set[str]) -> None:
	unknown_values = set()
	for fieldname in GRE_UBIGEO_FIELDS:
		values = frappe.get_all(
			"Nubefact Guia De Remision",
			filters={fieldname: ["is", "set"]},
			pluck=fieldname,
			distinct=True,
		)
		unknown_values.update(cstr(value).strip() for value in values if cstr(value).strip())

	unknown_values -= canonical_codes
	if unknown_values:
		frappe.logger("nubefact").warning(
			"Existing GRE records reference UBIGEO values absent from the INEI 2025 catalog: %s",
			", ".join(sorted(unknown_values)),
		)
