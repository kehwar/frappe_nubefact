from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import_xml import (
	parse_import_despatch_xml_payload,
)


@frappe.whitelist()
def crear_guia_de_remision_desde_archivo(file_name: str) -> str:
	file_doc = frappe.get_doc("File", file_name)
	content = file_doc.get_content()
	text = content.decode("utf-8-sig") if isinstance(content, bytes) else cstr(content)

	source_name = cstr(file_doc.file_name or file_doc.file_url or "").lower()
	if source_name.endswith(".json"):
		payload = parse_import_json_payload(text)
	elif source_name.endswith(".xml"):
		payload = parse_import_despatch_xml_payload(text)
	else:
		frappe.throw("Tipo de archivo no soportado. Solo se permiten archivos JSON y XML.")

	doc = frappe.new_doc("Nubefact Guia De Remision")
	apply_import_payload_to_doc(doc, payload)
	doc.flags.ignore_validate = True
	doc.insert()
	return doc.name


@frappe.whitelist()
def crear_guia_de_remision_desde_json(json_payload: str) -> str:
	payload = parse_import_json_payload(cstr(json_payload or ""))

	doc = frappe.new_doc("Nubefact Guia De Remision")
	apply_import_payload_to_doc(doc, payload)
	doc.flags.ignore_validate = True
	doc.insert()
	return doc.name


def apply_historical_import_payload_to_doc(doc: Document, payload: dict[str, Any]) -> None:
	"""Apply signed XML data through the controlled historical-validation path."""

	from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision import (
		HISTORICAL_IMPORT_CAPABILITY,
	)

	apply_import_payload_to_doc(doc, payload)
	doc.flags.nubefact_historical_import = HISTORICAL_IMPORT_CAPABILITY


def apply_import_payload_to_doc(doc: Document, payload: dict[str, Any]):
	scalar_map = {
		"tipo_de_comprobante": "tipo_de_comprobante",
		"serie": "serie",
		"cliente_tipo_de_documento": "cliente_tipo_de_documento",
		"cliente_numero_de_documento": "cliente_numero_de_documento",
		"cliente_denominacion": "cliente_denominacion",
		"cliente_direccion": "cliente_direccion",
		"cliente_email": "cliente_email",
		"cliente_email_1": "cliente_email_1",
		"cliente_email_2": "cliente_email_2",
		"destinatario_documento_tipo": "destinatario_documento_tipo",
		"destinatario_documento_numero": "destinatario_documento_numero",
		"destinatario_denominacion": "destinatario_denominacion",
		"motivo_de_traslado": "motivo_de_traslado",
		"tipo_de_transporte": "tipo_de_transporte",
		"peso_bruto_total": "peso_bruto_total",
		"peso_bruto_unidad_de_medida": "peso_bruto_unidad_de_medida",
		"numero_de_bultos": "numero_de_bultos",
		"transportista_documento_tipo": "transportista_documento_tipo",
		"transportista_documento_numero": "transportista_documento_numero",
		"transportista_denominacion": "transportista_denominacion",
		"transportista_placa_numero": "transportista_placa_numero",
		"tuc_vehiculo_principal": "tuc_vehiculo_principal",
		"conductor_documento_tipo": "conductor_documento_tipo",
		"conductor_documento_numero": "conductor_documento_numero",
		"conductor_denominacion": "conductor_denominacion",
		"conductor_nombre": "conductor_nombre",
		"conductor_apellidos": "conductor_apellidos",
		"conductor_numero_licencia": "conductor_numero_licencia",
		"mtc": "mtc",
		"sunat_envio_indicador": "sunat_envio_indicador",
		"subcontratador_documento_tipo": "subcontratador_documento_tipo",
		"subcontratador_documento_numero": "subcontratador_documento_numero",
		"subcontratador_denominacion": "subcontratador_denominacion",
		"pagador_servicio_documento_tipo_identidad": "pagador_servicio_documento_tipo_identidad",
		"pagador_servicio_documento_numero_identidad": "pagador_servicio_documento_numero_identidad",
		"pagador_servicio_denominacion": "pagador_servicio_denominacion",
		"punto_de_partida_ubigeo": "punto_de_partida_ubigeo",
		"punto_de_partida_direccion": "punto_de_partida_direccion",
		"punto_de_partida_codigo_establecimiento_sunat": "punto_de_partida_codigo_establecimiento_sunat",
		"punto_de_llegada_ubigeo": "punto_de_llegada_ubigeo",
		"punto_de_llegada_direccion": "punto_de_llegada_direccion",
		"punto_de_llegada_codigo_establecimiento_sunat": "punto_de_llegada_codigo_establecimiento_sunat",
		"formato_de_pdf": "formato_de_pdf",
		"observaciones": "observaciones",
		"documento_relacionado_codigo": "documento_relacionado_codigo",
		"motivo_de_traslado_otros_descripcion": "motivo_de_traslado_otros_descripcion",
	}

	for source_key, target_field in scalar_map.items():
		value = payload.get(source_key)
		if value is not None:
			doc.set(target_field, value)

	if "numero" in payload:
		doc.set("numero", payload.get("numero"))

	if payload.get("fecha_de_emision"):
		doc.set(
			"fecha_de_emision",
			_normalize_import_date(cstr(payload.get("fecha_de_emision"))),
		)

	if payload.get("fecha_de_inicio_de_traslado"):
		doc.set(
			"fecha_de_inicio_de_traslado",
			_normalize_import_date(cstr(payload.get("fecha_de_inicio_de_traslado"))),
		)

	if payload.get("fecha_de_entrega_al_transportista"):
		doc.set(
			"fecha_de_entrega_al_transportista",
			_normalize_import_date(cstr(payload.get("fecha_de_entrega_al_transportista"))),
		)

	if "enviar_automaticamente_al_cliente" in payload:
		doc.set(
			"enviar_automaticamente_al_cliente",
			1 if _to_bool(payload.get("enviar_automaticamente_al_cliente")) else 0,
		)

	known_top_level = {
		"operacion",
		"numero",
		"fecha_de_emision",
		"fecha_de_inicio_de_traslado",
		"fecha_de_entrega_al_transportista",
		"enviar_automaticamente_al_cliente",
		"items",
		"documento_relacionado",
		"vehiculos_secundarios",
		"conductores_secundarios",
		"custom",
		*scalar_map.keys(),
	}
	custom = _merge_custom_values(
		payload.get("custom"),
		{key: value for key, value in payload.items() if key not in known_top_level},
	)
	if custom:
		doc.set("custom", json.dumps(custom, ensure_ascii=False))

	doc.set("items", [])
	item_fields = {"unidad_de_medida", "codigo", "descripcion", "cantidad", "codigo_dam"}
	for row in payload.get("items") or []:
		values = {field: row.get(field) for field in item_fields}
		values["custom"] = _serialize_row_extensions(row, item_fields)
		doc.append("items", values)

	doc.set("documento_relacionado", [])
	related_fields = {"tipo", "serie", "numero"}
	for row in payload.get("documento_relacionado") or []:
		values = {field: row.get(field) for field in related_fields}
		values["custom"] = _serialize_row_extensions(row, related_fields)
		doc.append("documento_relacionado", values)

	doc.set("vehiculos_secundarios", [])
	vehicle_fields = {"placa_numero", "tuc"}
	for row in payload.get("vehiculos_secundarios") or []:
		values = {field: row.get(field) for field in vehicle_fields}
		values["custom"] = _serialize_row_extensions(row, vehicle_fields)
		doc.append("vehiculos_secundarios", values)

	doc.set("conductores_secundarios", [])
	driver_fields = {
		"documento_tipo",
		"documento_numero",
		"nombre",
		"apellidos",
		"numero_licencia",
	}
	for row in payload.get("conductores_secundarios") or []:
		values = {field: row.get(field) for field in driver_fields}
		values["custom"] = _serialize_row_extensions(row, driver_fields)
		doc.append("conductores_secundarios", values)


def parse_import_json_payload(text: str) -> dict[str, Any]:
	try:
		payload = json.loads(text)
	except json.JSONDecodeError:
		frappe.throw("Formato JSON inválido.")

	if not isinstance(payload, dict):
		frappe.throw("El payload JSON debe ser un objeto.")
	if payload.get("operacion") != "generar_guia":
		frappe.throw("El payload JSON debe usar la operación generar_guia.")
	if cstr(payload.get("tipo_de_comprobante")) not in {"7", "8"}:
		frappe.throw("El tipo de comprobante debe ser 7 u 8.")

	return payload


def _serialize_row_extensions(row: dict[str, Any], known_fields: set[str]) -> str | None:
	extensions = _merge_custom_values(
		row.get("custom"),
		{key: value for key, value in row.items() if key not in known_fields | {"custom"}},
	)
	return json.dumps(extensions, ensure_ascii=False) if extensions else None


def _merge_custom_values(raw_custom: Any, extensions: dict[str, Any]) -> dict[str, Any]:
	custom: dict[str, Any] = {}
	if isinstance(raw_custom, dict):
		custom.update(raw_custom)
	elif isinstance(raw_custom, str) and raw_custom.strip():
		try:
			parsed = json.loads(raw_custom)
		except json.JSONDecodeError:
			frappe.throw("El campo custom debe ser un objeto JSON válido.")
		if not isinstance(parsed, dict):
			frappe.throw("El campo custom debe ser un objeto JSON.")
		custom.update(parsed)
	elif raw_custom not in (None, ""):
		frappe.throw("El campo custom debe ser un objeto JSON.")
	custom.update(extensions)
	return custom


def _normalize_import_date(value: Any) -> str:
	text = cstr(value or "").strip()
	if not text:
		return ""

	if len(text) == 10 and text[2] == "-" and text[5] == "-":
		day, month, year = text.split("-")
		return f"{year}-{month}-{day}"

	return text


def _to_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value

	if isinstance(value, str):
		normalized = value.strip().lower()
		return normalized in {"1", "true", "yes", "y"}

	return bool(value)
