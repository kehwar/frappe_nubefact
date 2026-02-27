// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Delivery Note", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Import from JSON"), () => {
				open_import_dialog(frm);
			}, __("Actions"));
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Refresh SUNAT Status"), async () => {
				await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.refresh_sunat_status",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Refreshing SUNAT status..."),
				});

				await frm.reload_doc();
				frappe.show_alert({
					message: __("SUNAT status refreshed"),
					indicator: "green",
				});
			}, __("Actions"));
		}
	},
});

function open_import_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Import Delivery Note JSON"),
		fields: [
			{
				fieldname: "payload",
				fieldtype: "Code",
				label: __("JSON Payload"),
				options: "JSON",
				reqd: 1,
				description: __("Paste JSON in Nubefact example format (generar_guia)."),
			},
		],
		primary_action_label: __("Import"),
		primary_action: async (values) => {
			let payload;
			try {
				payload = JSON.parse(values.payload);
			} catch (error) {
				frappe.throw(__("Invalid JSON format."));
			}

			if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
				frappe.throw(__("JSON payload must be an object."));
			}

			await apply_payload_to_form(frm, payload);
			dialog.hide();
			frappe.show_alert({
				message: __("JSON imported to Delivery Note"),
				indicator: "green",
			});
		},
	});

	dialog.show();
}

async function apply_payload_to_form(frm, payload) {
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
		if (payload[sourceKey] !== undefined && payload[sourceKey] !== null) {
			await frm.set_value(targetField, payload[sourceKey]);
		}
	}

	if (Object.prototype.hasOwnProperty.call(payload, "numero")) {
		await frm.set_value("number", payload.numero ?? null);
	} else {
		await frm.set_value("number", null);
	}

	if (payload.fecha_de_emision) {
		await frm.set_value("issue_date", parse_nubefact_date(payload.fecha_de_emision));
	}

	if (payload.fecha_de_inicio_de_traslado) {
		await frm.set_value(
			"transfer_start_date",
			parse_nubefact_date(payload.fecha_de_inicio_de_traslado)
		);
	}

	if (payload.enviar_automaticamente_al_cliente !== undefined) {
		await frm.set_value(
			"auto_send_to_client",
			to_boolean(payload.enviar_automaticamente_al_cliente) ? 1 : 0
		);
	}

	frappe.model.clear_table(frm.doc, "items");
	for (const row of payload.items || []) {
		const child = frm.add_child("items");
		child.unit_of_measure = row.unidad_de_medida;
		child.item_code = row.codigo;
		child.description = row.descripcion;
		child.quantity = row.cantidad;
	}

	frappe.model.clear_table(frm.doc, "related_documents");
	for (const row of payload.documento_relacionado || []) {
		const child = frm.add_child("related_documents");
		child.document_type = row.tipo;
		child.series = row.serie;
		child.number = row.numero;
	}

	frappe.model.clear_table(frm.doc, "secondary_vehicles");
	for (const row of payload.vehiculos_secundarios || []) {
		const child = frm.add_child("secondary_vehicles");
		child.license_plate = row.placa_numero;
		child.tuc = row.tuc;
	}

	frappe.model.clear_table(frm.doc, "secondary_drivers");
	for (const row of payload.conductores_secundarios || []) {
		const child = frm.add_child("secondary_drivers");
		child.document_type = row.documento_tipo;
		child.document_number = row.documento_numero;
		child.first_name = row.nombre;
		child.last_name = row.apellidos;
		child.license_number = row.numero_licencia;
	}

	frm.refresh_fields([
		"items",
		"related_documents",
		"secondary_vehicles",
		"secondary_drivers",
	]);
}

function parse_nubefact_date(value) {
	if (typeof value !== "string") {
		return value;
	}

	const parts = value.split("-");
	if (parts.length !== 3) {
		return value;
	}

	const [day, month, year] = parts;
	return `${year}-${month}-${day}`;
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
