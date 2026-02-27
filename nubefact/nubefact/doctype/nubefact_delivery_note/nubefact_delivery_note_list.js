// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Delivery Note"] = {
	onload(listview) {
		listview.page.add_inner_button(__("JSON File"), async () => {
			await import_delivery_note_from_file([".json"]);
		});

		listview.page.add_inner_button(__("JSON Paste"), () => {
			open_json_paste_dialog();
		});

		listview.page.add_inner_button(__("XML File (T=7, V=8)"), async () => {
			await import_delivery_note_from_file([".xml", "text/xml"], {
				dialog_title: __("Import Delivery Note XML (Series: T=7, V=8)"),
			});
		});
	},
};

function open_json_paste_dialog() {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Delivery Note from JSON"),
		fields: [
			{
				fieldname: "json_payload",
				fieldtype: "Code",
				label: __("JSON Payload"),
				options: "JSON",
				reqd: 1,
				description: __(
					"Paste JSON in Nubefact example format (generar_guia). Parsing is handled on server."
				),
			},
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			try {
				const { message: deliveryNoteName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.create_delivery_note_from_import_json_text",
					args: {
						json_payload: values.json_payload,
					},
					freeze: true,
					freeze_message: __("Importing JSON..."),
				});

				dialog.hide();
				frappe.show_alert({
					message: __("Delivery Note created from JSON"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Delivery Note", deliveryNoteName);
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

async function import_delivery_note_from_file(allowedFileTypes, options = {}) {
	new frappe.ui.FileUploader({
		dialog_title: options.dialog_title || __("Import Delivery Note File"),
		allow_multiple: false,
		allow_toggle_private: false,
		restrictions: {
			allowed_file_types: allowedFileTypes,
		},
		on_success: async (file_doc) => {
			try {
				const { message: deliveryNoteName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.create_delivery_note_from_import_file",
					args: {
						file_name: file_doc.name,
					},
					freeze: true,
					freeze_message: __("Importing file..."),
				});

				frappe.show_alert({
					message: __("Delivery Note created from file"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Delivery Note", deliveryNoteName);
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
