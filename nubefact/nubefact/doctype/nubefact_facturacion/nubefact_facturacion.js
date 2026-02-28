// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Facturacion", {
	refresh(frm) {
		if (["Pending Response", "Voided"].includes(frm.doc.status || "Draft")) {
			frm.disable_form();
		}

		if (!frm.is_new()) {
			const watcher = nubefact.get_watcher(frm, "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion.refresh_sunat_status");
			watcher.on_refresh();
			watcher.schedule_if_needed();

			if (["Draft", "Error"].includes(frm.doc.status || "Draft")) {
				frm.add_custom_button(__("Send to Nubefact"), () => {
					frm.trigger("open_send_dialog");
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

			if (["Accepted", "Pending Response"].includes(frm.doc.status) && !frm.doc.voided) {
				frm.add_custom_button(__("Void in Nubefact"), () => {
					frm.trigger("open_void_dialog");
				});
			}

			if (["Accepted", "Voided"].includes(frm.doc.status)) {
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
		}
	},
	open_send_dialog(frm) {
		frappe.confirm(
			__("Confirmar el envío de este comprobante a Nubefact."),
			async () => {
				if (frm.is_dirty()) {
					await frm.save();
				}

				const { message } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion.send_to_nubefact",
					args: {
						name: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Enviando a Nubefact..."),
				});

				await frm.reload_doc();

				const has_error = message?.status === "Error";
				frappe.show_alert({
					message: has_error
						? __("El envío del comprobante falló. Estado actualizado a Error")
						: __("Comprobante enviado a Nubefact"),
					indicator: has_error ? "red" : "green",
				});
			}
		);
	},
	open_void_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Anular comprobante en Nubefact"),
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Small Text",
					label: __("Motivo de anulación"),
					reqd: 1,
				},
			],
			primary_action_label: __("Anular"),
			primary_action: async (values) => {
				const { message } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion.void_in_nubefact",
					args: {
						name: frm.doc.name,
						reason: values.reason,
					},
					freeze: true,
					freeze_message: __("Enviando solicitud de anulación a Nubefact..."),
				});

				dialog.hide();
				await frm.reload_doc();

				const has_error = message?.status === "Error";
				frappe.show_alert({
					message: has_error
						? __("La anulación del comprobante falló. Estado actualizado a Error")
						: __("Solicitud de anulación del comprobante enviada"),
					indicator: has_error ? "red" : "green",
				});
			},
		});

		dialog.show();
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
