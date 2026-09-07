from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import frappe
from frappe.utils import cstr

DESPATCH_ADVICE_NAMESPACE = "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"


def parse_import_despatch_xml_payload(text: str) -> dict[str, Any]:
	try:
		root = ET.fromstring(text)
	except ET.ParseError:
		frappe.throw("Formato XML inválido.")

	root_namespace, root_name = _xml_tag_parts(root.tag)
	if root_name == "ApplicationResponse":
		frappe.throw("El XML CDR no se puede usar para crear una guía. Use XML DespatchAdvice.")
	if root_name != "DespatchAdvice" or root_namespace != DESPATCH_ADVICE_NAMESPACE:
		frappe.throw("Tipo de XML no soportado. Se esperaba XML UBL DespatchAdvice con namespace válido.")

	full_number = _xml_get_nested_text(root, ["ID"])
	series, number = _split_gre_identity(full_number)
	document_type = _infer_document_type_from_series(series)
	if not document_type:
		frappe.throw("La serie del XML debe ser Txxx (GRE Remitente) o Vxxx (GRE Transportista).")

	sender_id_node = _party_id_node(root, "DespatchSupplierParty")
	recipient_id_node = _party_id_node(root, "DeliveryCustomerParty")
	customer_id_node = recipient_id_node if document_type == "7" else sender_id_node
	customer_party_name = "DeliveryCustomerParty" if document_type == "7" else "DespatchSupplierParty"
	customer_address = (
		_xml_get_nested_text(
			root,
			[
				"DespatchSupplierParty",
				"Party",
				"PartyLegalEntity",
				"RegistrationAddress",
				"AddressLine",
				"Line",
			],
		)
		if document_type == "8"
		else _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"],
		)[:100]
	)
	gross_weight_node = _xml_get_nested_node(root, ["Shipment", "GrossWeightMeasure"])

	payload: dict[str, Any] = {
		"tipo_de_comprobante": document_type,
		"serie": series,
		"numero": number,
		"fecha_de_emision": _normalize_import_date(_xml_get_nested_text(root, ["IssueDate"])),
		"fecha_de_inicio_de_traslado": _normalize_import_date(
			_xml_get_nested_text(
				root,
				["Shipment", "ShipmentStage", "TransitPeriod", "StartDate"],
			)
		),
		"fecha_de_entrega_al_transportista": _normalize_import_date(
			_xml_get_nested_text(
				root,
				["Shipment", "ShipmentStage", "LoadingTransportEvent", "OccurrenceDate"],
			)
		),
		"cliente_tipo_de_documento": (
			cstr(customer_id_node.get("schemeID")).strip() if customer_id_node is not None else ""
		),
		"cliente_numero_de_documento": (
			cstr(customer_id_node.text).strip()
			if customer_id_node is not None and customer_id_node.text
			else ""
		),
		"cliente_denominacion": _party_registration_name(root, customer_party_name),
		"cliente_direccion": customer_address,
		"motivo_de_traslado": _xml_get_nested_text(
			root,
			["Shipment", "HandlingCode"],
		),
		"tipo_de_transporte": _xml_get_nested_text(
			root,
			["Shipment", "ShipmentStage", "TransportModeCode"],
		),
		"peso_bruto_total": (
			cstr(gross_weight_node.text).strip()
			if gross_weight_node is not None and gross_weight_node.text
			else ""
		),
		"peso_bruto_unidad_de_medida": (
			cstr(gross_weight_node.get("unitCode")).strip()
			if gross_weight_node is not None and gross_weight_node.get("unitCode")
			else ""
		),
		"numero_de_bultos": _xml_get_nested_text(
			root,
			["Shipment", "TotalTransportHandlingUnitQuantity"],
		),
		"punto_de_partida_ubigeo": _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "Despatch", "DespatchAddress", "ID"],
		),
		"punto_de_partida_direccion": _xml_get_nested_text(
			root,
			[
				"Shipment",
				"Delivery",
				"Despatch",
				"DespatchAddress",
				"AddressLine",
				"Line",
			],
		),
		"punto_de_partida_codigo_establecimiento_sunat": _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "Despatch", "DespatchAddress", "AddressTypeCode"],
		),
		"punto_de_llegada_ubigeo": _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "DeliveryAddress", "ID"],
		),
		"punto_de_llegada_direccion": _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"],
		),
		"punto_de_llegada_codigo_establecimiento_sunat": _xml_get_nested_text(
			root,
			["Shipment", "Delivery", "DeliveryAddress", "AddressTypeCode"],
		),
		"observaciones": _clean_import_note(_xml_get_nested_text(root, ["Note"])),
		"transportista_documento_tipo": _xml_get_nested_attr(
			root,
			["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"],
			"schemeID",
		),
		"transportista_documento_numero": _xml_get_nested_text(
			root,
			["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"],
		),
		"transportista_denominacion": _xml_get_nested_text(
			root,
			[
				"Shipment",
				"ShipmentStage",
				"CarrierParty",
				"PartyLegalEntity",
				"RegistrationName",
			],
		),
		"mtc": _xml_get_nested_text(
			root,
			["Shipment", "ShipmentStage", "CarrierParty", "PartyLegalEntity", "CompanyID"],
		),
		"items": _parse_import_xml_items(root),
		"documento_relacionado": _parse_import_xml_related_documents(root),
		"vehiculos_secundarios": _parse_import_xml_secondary_vehicles(root),
	}
	payload.update(_parse_import_xml_transport(root))
	payload.update(_parse_import_xml_sunat_indicator(root))
	payload.update(_parse_import_xml_customs_code(payload))

	if cstr(document_type) == "8":
		payload["destinatario_documento_tipo"] = _node_scheme_id(recipient_id_node)
		payload["destinatario_documento_numero"] = _node_text(recipient_id_node)
		payload["destinatario_denominacion"] = _party_registration_name(root, "DeliveryCustomerParty")

	_validate_despatch_structure(payload)
	return {key: value for key, value in payload.items() if value not in (None, "", [])}


def _validate_despatch_structure(payload: dict[str, Any]) -> None:
	if not cstr(payload.get("fecha_de_emision")).strip():
		frappe.throw("El XML histórico no contiene la fecha de emisión estructural.")
	items = payload.get("items") or []
	if not items:
		frappe.throw("El XML histórico debe contener al menos un ítem.")
	for index, item in enumerate(items, start=1):
		missing = [
			fieldname
			for fieldname in ("unidad_de_medida", "descripcion", "cantidad")
			if not cstr(item.get(fieldname)).strip()
		]
		if missing:
			frappe.throw(
				f"El ítem #{index} del XML no contiene su estructura obligatoria: " + ", ".join(missing)
			)


def _parse_import_xml_items(root: ET.Element) -> list[dict[str, Any]]:
	items: list[dict[str, Any]] = []

	for line in _xml_findall(root, "DespatchLine"):
		delivered_quantity = _xml_get_nested_node(line, ["DeliveredQuantity"])
		item_node = _xml_get_nested_node(line, ["Item"])

		items.append(
			{
				"unidad_de_medida": (
					cstr(delivered_quantity.get("unitCode")).strip()
					if delivered_quantity is not None and delivered_quantity.get("unitCode")
					else ""
				),
				"codigo": _xml_get_nested_text(
					item_node,
					["SellersItemIdentification", "ID"],
				),
				"descripcion": _xml_get_nested_text(item_node, ["Description"])
				or _xml_get_nested_text(item_node, ["Name"]),
				"cantidad": (
					cstr(delivered_quantity.text).strip()
					if delivered_quantity is not None and delivered_quantity.text
					else ""
				),
				"codigo_dam": _parse_item_dam_code(item_node),
			}
		)

	return items


def _parse_import_xml_customs_code(payload: dict[str, Any]) -> dict[str, str]:
	motive = cstr(payload.get("motivo_de_traslado"))
	markers = {"08": {"10": "50", "18": "52"}, "09": {"40": "50", "48": "52"}}.get(motive)
	if not markers:
		return {}
	for item in payload.get("items") or []:
		customs_number = cstr(item.get("codigo_dam") or "")
		match = re.search(r"-(\d{2})-\d{6}$", customs_number)
		if match and match.group(1) in markers:
			return {"documento_relacionado_codigo": markers[match.group(1)]}
	return {}


def _parse_import_xml_related_documents(root: ET.Element) -> list[dict[str, Any]]:
	related_documents: list[dict[str, Any]] = []

	for reference in _xml_findall(root, "AdditionalDocumentReference"):
		full_number = _xml_get_nested_text(reference, ["ID"])
		series, number = _split_series_number(full_number)

		related_documents.append(
			{
				"tipo": _xml_get_nested_text(reference, ["DocumentTypeCode"]),
				"serie": series,
				"numero": number,
			}
		)

	return related_documents


def _parse_import_xml_transport(root: ET.Element) -> dict[str, Any]:
	driver_rows: list[dict[str, Any]] = []
	principal: dict[str, Any] = {}
	for driver in _xml_findall(_xml_get_nested_node(root, ["Shipment", "ShipmentStage"]), "DriverPerson"):
		id_node = _xml_get_nested_node(driver, ["ID"])
		values = {
			"documento_tipo": _node_scheme_id(id_node),
			"documento_numero": _node_text(id_node),
			"nombre": _xml_get_nested_text(driver, ["FirstName"]),
			"apellidos": _xml_get_nested_text(driver, ["FamilyName"]),
			"numero_licencia": _xml_get_nested_text(driver, ["IdentityDocumentReference", "ID"]),
		}
		if cstr(_xml_get_nested_text(driver, ["JobTitle"])).lower() == "secundario":
			driver_rows.append(values)
		elif not principal:
			principal = values

	transport_equipment = _xml_get_nested_node(
		root, ["Shipment", "TransportHandlingUnit", "TransportEquipment"]
	)
	result: dict[str, Any] = {
		"transportista_placa_numero": _xml_get_nested_text(transport_equipment, ["ID"])
		or _xml_get_nested_text(
			root,
			["Shipment", "ShipmentStage", "TransportMeans", "RoadTransport", "LicensePlateID"],
		),
		"tuc_vehiculo_principal": _xml_get_nested_text(
			transport_equipment, ["ApplicableTransportMeans", "RegistrationNationalityID"]
		),
		"conductores_secundarios": driver_rows,
	}
	if principal:
		result.update(
			{
				"conductor_documento_tipo": principal["documento_tipo"],
				"conductor_documento_numero": principal["documento_numero"],
				"conductor_nombre": principal["nombre"],
				"conductor_apellidos": principal["apellidos"],
				"conductor_numero_licencia": principal["numero_licencia"],
			}
		)
	return result


def _parse_import_xml_secondary_vehicles(root: ET.Element) -> list[dict[str, Any]]:
	equipment = _xml_get_nested_node(root, ["Shipment", "TransportHandlingUnit", "TransportEquipment"])
	vehicles: list[dict[str, Any]] = []
	for row in _xml_direct_children(equipment, "AttachedTransportEquipment"):
		vehicles.append(
			{
				"placa_numero": _xml_get_nested_text(row, ["ID"]),
				"tuc": _xml_get_nested_text(row, ["ApplicableTransportMeans", "RegistrationNationalityID"]),
			}
		)
	return vehicles


def _parse_import_xml_sunat_indicator(root: ET.Element) -> dict[str, str]:
	indicators = {
		"SUNAT_Envio_IndicadorPagadorFlete_Remitente": "01",
		"SUNAT_Envio_IndicadorPagadorFlete_Subcontratador": "02",
		"SUNAT_Envio_IndicadorPagadorFlete_Tercero": "03",
		"SUNAT_Envio_IndicadorRetornoVehiculoEnvaseVacio": "04",
		"SUNAT_Envio_IndicadorRetornoVehiculoVacio": "05",
		"SUNAT_Envio_IndicadorTrasladoVehiculoM1L": "06",
		"SUNAT_Envio_IndicadorVehiculoConductoresTransp": "07",
	}
	for node in _xml_findall(_xml_get_nested_node(root, ["Shipment"]), "SpecialInstructions"):
		code = indicators.get(_node_text(node))
		if code:
			return {"sunat_envio_indicador": code}
	return {}


def _parse_item_dam_code(item_node: ET.Element | None) -> str:
	number = ""
	series = ""
	for prop in _xml_direct_children(item_node, "AdditionalItemProperty"):
		name = _xml_get_nested_text(prop, ["Name"]).lower()
		value = _xml_get_nested_text(prop, ["Value"])
		if "numeración de la dam" in name or "numeracion de la dam" in name:
			number = value
		elif "serie en la dam" in name:
			series = value
	if series and number:
		return f"{series}/{number}"
	return number


def _party_id_node(root: ET.Element, party_name: str) -> ET.Element | None:
	node = _xml_get_nested_node(root, [party_name, "Party", "PartyIdentification", "ID"])
	if node is not None:
		return node
	return _xml_get_nested_node(root, [party_name, "CustomerAssignedAccountID"])


def _party_registration_name(root: ET.Element, party_name: str) -> str:
	return _xml_get_nested_text(root, [party_name, "Party", "PartyLegalEntity", "RegistrationName"])


def _node_scheme_id(node: ET.Element | None) -> str:
	return cstr(node.get("schemeID") if node is not None else "").strip()


def _node_text(node: ET.Element | None) -> str:
	return cstr(node.text if node is not None else "").strip()


def _xml_direct_children(node: ET.Element | None, local_name: str) -> list[ET.Element]:
	if node is None:
		return []
	return [child for child in list(node) if _xml_local_name(child.tag) == local_name]


def _xml_findall(node: ET.Element | None, local_name: str) -> list[ET.Element]:
	if node is None:
		return []

	return [child for child in node.iter() if _xml_local_name(child.tag) == local_name]


def _xml_get_nested_node(
	node: ET.Element | None,
	path: list[str],
) -> ET.Element | None:
	current = node

	for local_name in path:
		if current is None:
			return None
		current = _xml_first_child(current, local_name)

	return current


def _xml_get_nested_text(node: ET.Element | None, path: list[str]) -> str:
	found = _xml_get_nested_node(node, path)
	if found is None or not found.text:
		return ""
	return cstr(found.text).strip()


def _xml_get_nested_attr(node: ET.Element | None, path: list[str], attr_name: str) -> str:
	found = _xml_get_nested_node(node, path)
	if found is None:
		return ""
	return cstr(found.get(attr_name) or "").strip()


def _xml_first_child(node: ET.Element, local_name: str) -> ET.Element | None:
	for child in list(node):
		if _xml_local_name(child.tag) == local_name:
			return child
	return None


def _xml_local_name(tag: str) -> str:
	return _xml_tag_parts(tag)[1]


def _xml_tag_parts(tag: str) -> tuple[str, str]:
	if tag.startswith("{") and "}" in tag:
		namespace, local_name = tag[1:].split("}", 1)
		return namespace, local_name
	return "", tag


def _split_gre_identity(value: Any) -> tuple[str, str]:
	series, number_text = _split_series_number(value)
	series = series.strip().upper()
	if not re.fullmatch(r"[TV][A-Z0-9]{3}", series):
		frappe.throw("La serie del XML debe tener exactamente cuatro caracteres válidos.")
	if not re.fullmatch(r"\d+", number_text.strip()):
		frappe.throw("El número del XML debe ser un entero positivo.")
	number = int(number_text)
	if not 1 <= number <= 99_999_999:
		frappe.throw("El número del XML debe ser un entero de 1 a 8 dígitos.")
	return series, str(number)


def _split_series_number(value: Any) -> tuple[str, str]:
	text = cstr(value or "").strip()
	if not text or "-" not in text:
		return text, ""
	series, *rest = text.split("-")
	return series, "-".join(rest)


def _infer_document_type_from_series(series: Any) -> str:
	normalized = cstr(series or "").strip().upper()
	if re.fullmatch(r"T[A-Z0-9]{3}", normalized):
		return "7"
	if re.fullmatch(r"V[A-Z0-9]{3}", normalized):
		return "8"
	return ""


def _normalize_import_date(value: Any) -> str:
	text = cstr(value or "").strip()
	if not text:
		return ""

	if len(text) == 10 and text[2] == "-" and text[5] == "-":
		day, month, year = text.split("-")
		return f"{year}-{month}-{day}"

	return text


def _clean_import_note(value: Any) -> str:
	text = cstr(value or "").strip()
	if text.lower().startswith("obs:"):
		return text[4:].strip()
	return text
