// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Delivery Note", {
	refresh(frm) {
		if (["Pending Response", "Accepted"].includes(frm.doc.status || "Draft")) {
			frm.disable_form();
		}

		if (["Draft", "Error"].includes(frm.doc.status || "Draft")) {
			frm.add_custom_button(__("Send to Nubefact"), () => {
				open_send_dialog(frm);
			});
		}

		if (["Draft", "Pending Response", "Accepted", "Error"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Refresh SUNAT Status"), async () => {
				await watcher.refresh_now_and_continue();

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

		if (!frm.is_new()){
            const watcher = nubefact.get_watcher(frm, "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.refresh_sunat_status");
            watcher.on_refresh();
            watcher.schedule_if_needed();
        }
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
	frappe.confirm(
		__("Confirm sending this Delivery Note to Nubefact."),
		async () => {
			if (frm.is_dirty()) {
				await frm.save();
			}

			const { message } = await frappe.call({
				method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.send_to_nubefact",
				args: {
					name: frm.doc.name,
				},
				freeze: true,
				freeze_message: __("Sending to Nubefact..."),
			});

			await frm.reload_doc();

			const has_error = message?.status === "Error";
			frappe.show_alert({
				message: has_error
					? __("Delivery Note send failed. Status updated to Error")
					: __("Delivery Note sent to Nubefact"),
				indicator: has_error ? "red" : "green",
			});
		}
	);
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
