// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Delivery Note", {
	refresh(frm) {
		if (frm.doc.status === "Accepted") {
			frm.disable_form();
		}

		if (["Draft", "Error"].includes(frm.doc.status || "Draft")) {
			frm.add_custom_button(__("Send to Nubefact"), () => {
				open_send_dialog(frm);
			});
		}

		if (["Draft", "Pending Response", "Accepted", "Error"].includes(frm.doc.status)) {
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
			});
		}

		if (frm.doc.status === "Accepted") {
			frm.add_custom_button(__("PDF"), () => {
				download_file_from_url(frm, "pdf_url", "PDF");
			}, "Download");

			frm.add_custom_button(__("XML"), () => {
				download_file_from_url(frm, "xml_url", "XML");
			}, "Download");

			frm.add_custom_button(__("CDR"), () => {
				download_file_from_url(frm, "cdr_url", "CDR");
			}, "Download");
		}

		frm.add_custom_button(__("Help"), () => {
			open_help_dialog(frm);
		});
	},
});

function download_file_from_url(frm, fieldname, label) {
	const url = frm.doc[fieldname];

	if (!url) {
		frappe.msgprint(__("{0} URL is not available yet.", [label]));
		return;
	}

	window.open(url, "_blank");
}

function open_send_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Send to Nubefact"),
		fields: [
			{
				fieldname: "confirmation_text",
				fieldtype: "HTML",
				options: `<div class="text-muted">${__("Confirm sending this Delivery Note to Nubefact.")}</div>`,
			},
			{
				fieldname: "skip_required_fields_validation",
				fieldtype: "Check",
				label: __("Skip required fields validation"),
				default: 0,
			},
		],
		primary_action_label: __("Send"),
		primary_action: async (values) => {
			if (frm.is_dirty()) {
				await frm.save();
			}

			await frappe.call({
				method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.send_to_nubefact",
				args: {
					name: frm.doc.name,
					skip_required_fields_validation: values.skip_required_fields_validation ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Sending to Nubefact..."),
			});

			dialog.hide();
			await frm.reload_doc();
			frappe.show_alert({
				message: __("Delivery Note sent to Nubefact"),
				indicator: "green",
			});
		},
	});

	dialog.show();
}

function open_help_dialog(frm) {
	const requiredFields = [
		"document_type",
		"series",
		"issue_date",
		"transfer_start_date",
		"client_document_type",
		"client_document_number",
		"client_name",
		"client_address",
		"transfer_reason",
		"transport_type",
		"gross_total_weight",
		"weight_unit",
		"number_of_packages",
		"destination_ubigeo",
		"destination_address",
		"items (at least one row)",
		"items.unit_of_measure",
		"items.item_code",
		"items.description",
		"items.quantity",
		"recipient_document_type (when document_type = 8)",
		"recipient_document_number (when document_type = 8)",
		"recipient_name (when document_type = 8)",
	];

	const selectMeanings = [
		{
			field: "document_type",
			values: ["7 = GRE Remitente", "8 = GRE Transportista"],
		},
		{
			field: "status",
			values: [
				"Draft = Not sent yet",
				"Pending Response = Sent, waiting SUNAT acceptance",
				"Accepted = Accepted by SUNAT",
				"Error = Last send failed",
			],
		},
		{
			field: "transfer_reason",
			values: [
				"01 Sale",
				"02 Purchase",
				"04 Consignment trade",
				"05 Consignment",
				"06 Import",
				"07 Export",
				"08 Sale with delivery to third party",
				"09 Transfer between company establishments",
				"13 Others",
				"14 Sale subject to confirmation by buyer",
				"18 Transfer issuer ITINERANT CP",
				"19 Transfer to primary production zone",
			],
		},
		{
			field: "transport_type",
			values: ["01 Private", "02 Public"],
		},
		{
			field: "weight_unit",
			values: ["KGM Kilogram", "TNE Ton"],
		},
		{
			field: "client_document_type / recipient_document_type / carrier_document_type",
			values: [
				"6 RUC",
				"1 DNI",
				"4 Carnet de Extranjería",
				"7 Pasaporte",
				"A Cédula Diplomática",
				"0 Doc. No Domiciliado / Otros",
			],
		},
		{
			field: "driver_document_type / secondary_drivers.document_type",
			values: ["1 DNI", "4 Carnet de Extranjería", "7 Pasaporte"],
		},
		{
			field: "pdf_format",
			values: ["A4", "A5", "TICKET"],
		},
		{
			field: "related_documents.document_type",
			values: [
				"01 Factura",
				"02 Boleta de Venta",
				"03 Nota de Crédito",
				"04 Nota de Débito",
				"06 Carta de Porte Aéreo",
				"09 Guía de Remisión Remitente",
				"12 Ticket de Máquina Registradora",
				"31 Guía de Remisión Transportista",
				"50 DUA",
				"80 Comprobante no emitido",
			],
		},
	];

	const requiredHtml = `
		<div style="margin-bottom: 12px;">
			<div style="font-weight: 600; margin-bottom: 6px;">${__("Required fields for Send to Nubefact")}</div>
			<ul style="margin: 0; padding-left: 18px; max-height: 210px; overflow: auto;">
				${requiredFields.map((fieldname) => `<li>${frappe.utils.escape_html(fieldname)}</li>`).join("")}
			</ul>
		</div>
	`;

	const meaningsHtml = `
		<div>
			<div style="font-weight: 600; margin-bottom: 6px;">${__("Select field values")}</div>
			<div style="max-height: 280px; overflow: auto; border: 1px solid var(--border-color); border-radius: 6px; padding: 8px;">
				${selectMeanings
					.map(
						(item) => `
							<div style="margin-bottom: 10px;">
								<div style="font-weight: 600;">${frappe.utils.escape_html(item.field)}</div>
								<ul style="margin: 2px 0 0; padding-left: 18px;">
									${item.values.map((value) => `<li>${frappe.utils.escape_html(value)}</li>`).join("")}
								</ul>
							</div>
						`
					)
					.join("")}
			</div>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: __("Delivery Note Help"),
		fields: [
			{
				fieldname: "help_html",
				fieldtype: "HTML",
				options: `${requiredHtml}${meaningsHtml}`,
			},
		],
		primary_action_label: __("Close"),
		primary_action: () => dialog.hide(),
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
