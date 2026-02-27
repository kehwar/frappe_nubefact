// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Delivery Note"] = {
	onload(listview) {
		listview.page.add_menu_item(__("Create from JSON File"), async () => {
			await import_delivery_note_from_file(".json", "json");
		});

		listview.page.add_menu_item(__("Create from XML File"), async () => {
			await import_delivery_note_from_file(".xml,text/xml", "xml");
		});
	},
};

async function import_delivery_note_from_file(accept, type) {
	try {
		const fileText = await pick_file_text({ accept });
		const payload = type === "json"
			? parse_json_payload(fileText)
			: parse_despatch_xml_to_payload(fileText);

		open_new_delivery_note_with_payload(payload);
	} catch (error) {
		frappe.msgprint({
			title: __("Import failed"),
			indicator: "red",
			message: frappe.utils.escape_html(error?.message || __("Could not import file.")),
		});
	}
}

function pick_file_text({ accept }) {
	return new Promise((resolve, reject) => {
		const input = document.createElement("input");
		input.type = "file";
		input.accept = accept;
		input.style.display = "none";
		document.body.appendChild(input);

		input.addEventListener("change", () => {
			const file = input.files?.[0];
			input.remove();

			if (!file) {
				reject(new Error(__("No file selected.")));
				return;
			}

			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result || ""));
			reader.onerror = () => reject(new Error(__("Could not read selected file.")));
			reader.readAsText(file);
		});

		input.click();
	});
}

function parse_json_payload(fileText) {
	let payload;
	try {
		payload = JSON.parse(fileText);
	} catch {
		throw new Error(__("Invalid JSON format."));
	}

	if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
		throw new Error(__("JSON payload must be an object."));
	}

	return payload;
}

function parse_despatch_xml_to_payload(fileText) {
	const parser = new DOMParser();
	const xml = parser.parseFromString(fileText, "application/xml");
	const parserError = xml.querySelector("parsererror");
	if (parserError) {
		throw new Error(__("Invalid XML format."));
	}

	const rootName = xml.documentElement?.localName || "";
	if (rootName === "ApplicationResponse") {
		throw new Error(__("CDR XML cannot be used to create a Delivery Note. Use DespatchAdvice XML."));
	}
	if (rootName !== "DespatchAdvice") {
		throw new Error(__("Unsupported XML type. Expected SUNAT DespatchAdvice XML."));
	}

	const fullNumber = get_first_text(xml, "ID") || "";
	const [series = "", number = ""] = split_series_number(fullNumber);
	const inferredDocumentType = infer_document_type_from_series(series);

	const customerNode = first_node(xml, "DeliveryCustomerParty");
	const customerIdNode = first_node(customerNode, "ID");

	const issueDate = normalize_date(get_first_text(xml, "IssueDate"));
	const transferStartDate = normalize_date(
		get_nested_text(xml, ["Shipment", "ShipmentStage", "TransitPeriod", "StartDate"])
	);

	const grossWeightNode = first_node(xml, "GrossWeightMeasure");
	const payload = {
		tipo_de_comprobante: inferredDocumentType,
		serie: series,
		numero: number,
		fecha_de_emision: issueDate,
		fecha_de_inicio_de_traslado: transferStartDate,
		cliente_tipo_de_documento: customerIdNode?.getAttribute("schemeID") || "",
		cliente_numero_de_documento: get_text(customerIdNode),
		cliente_denominacion: get_nested_text(customerNode, ["Party", "PartyLegalEntity", "RegistrationName"]),
		cliente_direccion: get_nested_text(xml, ["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"]),
		motivo_de_traslado: get_nested_text(xml, ["Shipment", "HandlingCode"]),
		tipo_de_transporte: get_nested_text(xml, ["Shipment", "ShipmentStage", "TransportModeCode"]),
		peso_bruto_total: get_text(grossWeightNode),
		peso_bruto_unidad_de_medida: grossWeightNode?.getAttribute("unitCode") || "",
		numero_de_bultos: get_first_text(xml, "TotalTransportHandlingUnitQuantity") || "1",
		punto_de_partida_ubigeo: get_nested_text(xml, ["Shipment", "Delivery", "Despatch", "DespatchAddress", "ID"]),
		punto_de_partida_direccion: get_nested_text(xml, ["Shipment", "Delivery", "Despatch", "DespatchAddress", "AddressLine", "Line"]),
		punto_de_llegada_ubigeo: get_nested_text(xml, ["Shipment", "Delivery", "DeliveryAddress", "ID"]),
		punto_de_llegada_direccion: get_nested_text(xml, ["Shipment", "Delivery", "DeliveryAddress", "AddressLine", "Line"]),
		observaciones: clean_note(get_first_text(xml, "Note")),
		transportista_documento_tipo: get_nested_attr(xml, ["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"], "schemeID"),
		transportista_documento_numero: get_nested_text(xml, ["Shipment", "ShipmentStage", "CarrierParty", "PartyIdentification", "ID"]),
		transportista_denominacion: get_nested_text(xml, ["Shipment", "ShipmentStage", "CarrierParty", "PartyLegalEntity", "RegistrationName"]),
		items: parse_xml_items(xml),
		documento_relacionado: parse_xml_related_documents(xml),
	};

	if (inferredDocumentType === "8") {
		payload.destinatario_documento_tipo = payload.cliente_tipo_de_documento;
		payload.destinatario_documento_numero = payload.cliente_numero_de_documento;
		payload.destinatario_denominacion = payload.cliente_denominacion;
	}

	return payload;
}

function open_new_delivery_note_with_payload(payload) {
	frappe.new_doc("Nubefact Delivery Note", {}, (doc) => {
		apply_payload_to_doc(doc, payload);
	});

	frappe.show_alert({
		message: __("New Delivery Note created from file"),
		indicator: "green",
	});
}

function apply_payload_to_doc(doc, payload) {
	const scalarMap = {
		tipo_de_comprobante: "document_type",
		serie: "series",
		cliente_tipo_de_documento: "client_document_type",
		cliente_numero_de_documento: "client_document_number",
		cliente_denominacion: "client_name",
		cliente_direccion: "client_address",
		cliente_email: "client_email",
		cliente_email_1: "client_email_1",
		cliente_email_2: "client_email_2",
		destinatario_documento_tipo: "recipient_document_type",
		destinatario_documento_numero: "recipient_document_number",
		destinatario_denominacion: "recipient_name",
		motivo_de_traslado: "transfer_reason",
		tipo_de_transporte: "transport_type",
		peso_bruto_total: "gross_total_weight",
		peso_bruto_unidad_de_medida: "weight_unit",
		numero_de_bultos: "number_of_packages",
		transportista_documento_tipo: "carrier_document_type",
		transportista_documento_numero: "carrier_document_number",
		transportista_denominacion: "carrier_name",
		transportista_placa_numero: "vehicle_license_plate",
		conductor_documento_tipo: "driver_document_type",
		conductor_documento_numero: "driver_document_number",
		conductor_nombre: "driver_first_name",
		conductor_apellidos: "driver_last_name",
		conductor_numero_licencia: "driver_license_number",
		punto_de_partida_ubigeo: "origin_ubigeo",
		punto_de_partida_direccion: "origin_address",
		punto_de_partida_codigo_establecimiento_sunat: "origin_sunat_code",
		punto_de_llegada_ubigeo: "destination_ubigeo",
		punto_de_llegada_direccion: "destination_address",
		punto_de_llegada_codigo_establecimiento_sunat: "destination_sunat_code",
		formato_de_pdf: "pdf_format",
		observaciones: "observations",
	};

	for (const [sourceKey, targetField] of Object.entries(scalarMap)) {
		const value = payload[sourceKey];
		if (value !== undefined && value !== null) {
			doc[targetField] = value;
		}
	}

	if (Object.prototype.hasOwnProperty.call(payload, "numero")) {
		doc.number = payload.numero ?? null;
	}

	if (payload.fecha_de_emision) {
		doc.issue_date = normalize_date(payload.fecha_de_emision);
	}

	if (payload.fecha_de_inicio_de_traslado) {
		doc.transfer_start_date = normalize_date(payload.fecha_de_inicio_de_traslado);
	}

	if (payload.enviar_automaticamente_al_cliente !== undefined) {
		doc.auto_send_to_client = to_boolean(payload.enviar_automaticamente_al_cliente) ? 1 : 0;
	}

	set_child_table(doc, "items", "Nubefact Delivery Note Item", payload.items || [], (child, row) => {
		child.unit_of_measure = row.unidad_de_medida;
		child.item_code = row.codigo;
		child.description = row.descripcion;
		child.quantity = row.cantidad;
	});

	set_child_table(
		doc,
		"related_documents",
		"Nubefact Delivery Note Related Document",
		payload.documento_relacionado || [],
		(child, row) => {
			child.document_type = row.tipo;
			child.series = row.serie;
			child.number = row.numero;
		}
	);

	set_child_table(
		doc,
		"secondary_vehicles",
		"Nubefact Delivery Note Secondary Vehicle",
		payload.vehiculos_secundarios || [],
		(child, row) => {
			child.license_plate = row.placa_numero;
			child.tuc = row.tuc;
		}
	);

	set_child_table(
		doc,
		"secondary_drivers",
		"Nubefact Delivery Note Secondary Driver",
		payload.conductores_secundarios || [],
		(child, row) => {
			child.document_type = row.documento_tipo;
			child.document_number = row.documento_numero;
			child.first_name = row.nombre;
			child.last_name = row.apellidos;
			child.license_number = row.numero_licencia;
		}
	);
}

function set_child_table(doc, fieldname, childDoctype, rows, mapper) {
	doc[fieldname] = [];
	for (const row of rows) {
		const child = frappe.model.add_child(doc, childDoctype, fieldname);
		mapper(child, row || {});
	}
}

function parse_xml_items(xml) {
	return Array.from(xml.getElementsByTagNameNS("*", "DespatchLine")).map((line) => {
		const deliveredQuantity = first_node(line, "DeliveredQuantity");
		const itemNode = first_node(line, "Item");
		const sellersItem = first_node(itemNode, "SellersItemIdentification");

		return {
			unidad_de_medida: deliveredQuantity?.getAttribute("unitCode") || "NIU",
			codigo: get_first_text(sellersItem, "ID"),
			descripcion: get_first_text(itemNode, "Description"),
			cantidad: get_text(deliveredQuantity),
		};
	});
}

function parse_xml_related_documents(xml) {
	return Array.from(xml.getElementsByTagNameNS("*", "AdditionalDocumentReference")).map((node) => {
		const id = get_first_text(node, "ID");
		const [serie = "", numero = ""] = split_series_number(id);

		return {
			tipo: get_first_text(node, "DocumentTypeCode"),
			serie,
			numero,
		};
	});
}

function first_node(node, localName) {
	if (!node) {
		return null;
	}

	const matches = node.getElementsByTagNameNS("*", localName);
	return matches.length ? matches[0] : null;
}

function get_first_text(node, localName) {
	return get_text(first_node(node, localName));
}

function get_text(node) {
	return (node?.textContent || "").trim();
}

function get_nested_text(node, path) {
	const found = get_nested_node(node, path);
	return get_text(found);
}

function get_nested_attr(node, path, attrName) {
	const found = get_nested_node(node, path);
	return found?.getAttribute(attrName) || "";
}

function get_nested_node(node, path) {
	let current = node;
	for (const localName of path) {
		if (!current) {
			return null;
		}
		current = first_node(current, localName);
	}
	return current;
}

function split_series_number(value) {
	if (typeof value !== "string" || !value.includes("-")) {
		return [value || "", ""];
	}

	const [series, ...rest] = value.split("-");
	return [series || "", rest.join("-") || ""];
}

function infer_document_type_from_series(series) {
	const cleanSeries = (series || "").trim().toUpperCase();
	if (cleanSeries.startsWith("T")) {
		return "7";
	}
	if (cleanSeries.startsWith("v")) {
		return "8";
	}
	return "";
}

function normalize_date(value) {
	if (typeof value !== "string") {
		return value;
	}

	const trimmed = value.trim();
	if (!trimmed) {
		return trimmed;
	}

	if (/^\d{2}-\d{2}-\d{4}$/.test(trimmed)) {
		const [day, month, year] = trimmed.split("-");
		return `${year}-${month}-${day}`;
	}

	if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
		return trimmed;
	}

	return trimmed;
}

function clean_note(note) {
	if (!note) {
		return "";
	}

	return note.replace(/^Obs:\s*/i, "").trim();
}

function to_boolean(value) {
	if (typeof value === "boolean") {
		return value;
	}

	if (typeof value === "string") {
		return value.toLowerCase() === "true" || value === "1";
	}

	return Boolean(value);
}
