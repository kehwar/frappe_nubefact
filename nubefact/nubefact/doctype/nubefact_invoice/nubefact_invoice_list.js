// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Invoice"] = {
	onload(listview) {
		listview.page.add_inner_button(__("File"), async () => {
			await import_invoice_from_file([".json"]);
		}, "Import");

		listview.page.add_inner_button(__("JSON"), () => {
			open_json_paste_dialog();
		}, "Import");
	},
};

function open_json_paste_dialog() {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Invoice from JSON"),
		fields: [
			{
				fieldname: "json_payload",
				fieldtype: "Code",
				label: __("JSON Payload"),
				options: "JSON",
				reqd: 1,
				description: __(
					"Paste JSON in Nubefact example format (generar_comprobante). Parsing is handled on server."
				),
			},
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			try {
				const { message: invoiceName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_invoice.nubefact_invoice_import.create_invoice_from_import_json_text",
					args: {
						json_payload: values.json_payload,
					},
					freeze: true,
					freeze_message: __("Importing JSON..."),
				});

				dialog.hide();
				frappe.show_alert({
					message: __("Invoice created from JSON"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Invoice", invoiceName);
			} catch (error) {
				frappe.msgprint({
					title: __("Import failed"),
					indicator: "red",
					message: frappe.utils.escape_html(
						error?.message || __("Could not import JSON.")
					),
				});
			}
		},
	});

	dialog.show();
}

async function import_invoice_from_file(allowedFileTypes, options = {}) {
	new frappe.ui.FileUploader({
		dialog_title: options.dialog_title || __("Import Invoice File"),
		allow_multiple: false,
		allow_toggle_private: false,
		restrictions: {
			allowed_file_types: allowedFileTypes,
		},
		on_success: async (file_doc) => {
			try {
				const { message: invoiceName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_invoice.nubefact_invoice_import.create_invoice_from_import_file",
					args: {
						file_name: file_doc.name,
					},
					freeze: true,
					freeze_message: __("Importing file..."),
				});

				frappe.show_alert({
					message: __("Invoice created from file"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Invoice", invoiceName);
			} catch (error) {
				frappe.msgprint({
					title: __("Import failed"),
					indicator: "red",
					message: frappe.utils.escape_html(
						error?.message || __("Could not import file.")
					),
				});
			}
		},
	});
}
