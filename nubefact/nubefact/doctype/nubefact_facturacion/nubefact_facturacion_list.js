// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Facturacion"] = {
	onload(listview) {
			listview.page.add_inner_button(__("Archivo"), async () => {
				await import_invoice_from_file([".json"]);
			}, "Importar");

			listview.page.add_inner_button(__("JSON"), () => {
				open_json_paste_dialog();
			}, "Importar");
		},
};

function open_json_paste_dialog() {
	const dialog = new frappe.ui.Dialog({
		title: __("Crear comprobante desde JSON"),
		fields: [
			{
				fieldname: "json_payload",
				fieldtype: "Code",
				label: __("Payload JSON"),
				options: "JSON",
				reqd: 1,
				description: __(
					"Pegue JSON en formato de ejemplo de Nubefact (generar_comprobante). El análisis se maneja en el servidor."
				),
			},
		],
		primary_action_label: __("Crear"),
		primary_action: async (values) => {
			try {
				const { message: invoiceName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_import.create_invoice_from_import_json_text",
					args: {
						json_payload: values.json_payload,
					},
					freeze: true,
					freeze_message: __("Importando JSON..."),
				});

				dialog.hide();
				frappe.show_alert({
					message: __("Comprobante creado desde JSON"),
					indicator: "green",
				});

			frappe.set_route("Form", "Nubefact Facturacion", invoiceName);
			} catch (error) {
				frappe.msgprint({
					title: __("Importación fallida"),
					indicator: "red",
					message: frappe.utils.escape_html(
						error?.message || __("No se pudo importar el JSON.")
					),
				});
			}
		},
	});

	dialog.show();
}

async function import_invoice_from_file(allowedFileTypes, options = {}) {
	new frappe.ui.FileUploader({
		dialog_title: options.dialog_title || __("Importar archivo de comprobante"),
		allow_multiple: false,
		allow_toggle_private: false,
		restrictions: {
			allowed_file_types: allowedFileTypes,
		},
		on_success: async (file_doc) => {
			try {
				const { message: invoiceName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_import.create_invoice_from_import_file",
					args: {
						file_name: file_doc.name,
					},
					freeze: true,
					freeze_message: __("Importando archivo..."),
				});

				frappe.show_alert({
					message: __("Comprobante creado desde archivo"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Facturacion", invoiceName);
			} catch (error) {
				frappe.msgprint({
					title: __("Importación fallida"),
					indicator: "red",
					message: frappe.utils.escape_html(
						error?.message || __("No se pudo importar el archivo.")
					),
				});
			}
		},
	});
}
