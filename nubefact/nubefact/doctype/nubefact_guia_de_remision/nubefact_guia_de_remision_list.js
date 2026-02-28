// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Guia de Remision"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Archivo"), async () => {
			await importar_guia_de_remision_desde_archivo([".json", ".xml", "text/xml"]);
		}, "Importar");

		listview.page.add_inner_button(__("JSON"), () => {
			abrir_dialogo_pegar_json();
		}, "Importar");
	},
};

function abrir_dialogo_pegar_json() {
	const dialog = new frappe.ui.Dialog({
		title: __("Crear Guía de Remisión desde JSON"),
		fields: [
			{
				fieldname: "json_payload",
				fieldtype: "Code",
				label: __("Payload JSON"),
				options: "JSON",
				reqd: 1,
				description: __(
					"Pegue JSON con formato de ejemplo de Nubefact (generar_guia). El parseo se realiza en el servidor."
				),
			},
		],
		primary_action_label: __("Crear"),
		primary_action: async (values) => {
			try {
				const { message: guiaName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import.crear_guia_de_remision_desde_json",
					args: {
						json_payload: values.json_payload,
					},
					freeze: true,
					freeze_message: __("Importando JSON..."),
				});

				dialog.hide();
				frappe.show_alert({
					message: __("Guía de Remisión creada desde JSON"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Guia de Remision", guiaName);
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

async function importar_guia_de_remision_desde_archivo(allowedFileTypes, options = {}) {
	new frappe.ui.FileUploader({
		dialog_title: options.dialog_title || __("Importar archivo de Guía de Remisión"),
		allow_multiple: false,
		allow_toggle_private: false,
		restrictions: {
			allowed_file_types: allowedFileTypes,
		},
		on_success: async (file_doc) => {
			try {
				const { message: guiaName } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_import.crear_guia_de_remision_desde_archivo",
					args: {
						file_name: file_doc.name,
					},
					freeze: true,
					freeze_message: __("Importando archivo..."),
				});

				frappe.show_alert({
					message: __("Guía de Remisión creada desde archivo"),
					indicator: "green",
				});

				frappe.set_route("Form", "Nubefact Guia de Remision", guiaName);
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
