// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Guia de Remision", {
	refresh(frm) {
		if (["Pendiente de Respuesta", "Aceptada"].includes(frm.doc.estado || "Borrador")) {
			frm.disable_form();
		}

		if (!frm.is_new()) {
			const watcher = nubefact.get_watcher(
				frm,
				"nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.refrescar_estado_sunat"
			);
			watcher.on_refresh();
			watcher.schedule_if_needed();

			if (["Borrador", "Error"].includes(frm.doc.estado || "Borrador")) {
				frm.add_custom_button(__("Enviar a Nubefact"), () => {
					frm.trigger("open_send_dialog");
				});
			}

			if (["Borrador", "Pendiente de Respuesta", "Aceptada", "Error"].includes(frm.doc.estado)) {
				frm.add_custom_button(__("Refrescar estado SUNAT"), async () => {
					await watcher.refresh_now_and_continue();

					frappe.show_alert({
						message: __("Estado SUNAT actualizado"),
						indicator: "green",
					});
				});
			}

			if (frm.doc.estado === "Aceptada") {
				frm.add_custom_button(__("PDF"), () => {
					download_file_from_url(frm, "enlace_del_pdf", "PDF");
				}, "Descargar");

				frm.add_custom_button(__("XML"), () => {
					download_file_from_url(frm, "enlace_del_xml", "XML");
				}, "Descargar");

				frm.add_custom_button(__("CDR"), () => {
					download_file_from_url(frm, "enlace_del_cdr", "CDR");
				}, "Descargar");
			}
		}

		frm.add_custom_button(__("Ayuda"), () => {
			frm.trigger("open_help_dialog");
		});
	},
	open_send_dialog(frm) {
		frappe.confirm(
			__("¿Confirmas enviar esta Guía de Remisión a Nubefact?"),
			async () => {
				if (frm.is_dirty()) {
					await frm.save();
				}

				const { message } = await frappe.call({
					method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.enviar_a_nubefact",
					args: {
						name: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Enviando a Nubefact..."),
				});

				await frm.reload_doc();

				const has_error = message?.estado === "Error";
				frappe.show_alert({
					message: has_error
						? __("Falló el envío de la guía. El estado cambió a Error")
						: __("Guía de Remisión enviada a Nubefact"),
					indicator: has_error ? "red" : "green",
				});
			}
		);
	},
	open_help_dialog(frm) {
		const requiredFields = [
			"tipo_de_comprobante",
			"serie",
			"fecha_de_emision",
			"fecha_de_inicio_de_traslado",
			"cliente_tipo_de_documento",
			"cliente_numero_de_documento",
			"cliente_denominacion",
			"cliente_direccion",
			"motivo_de_traslado",
			"tipo_de_transporte",
			"peso_bruto_total",
			"peso_bruto_unidad_de_medida",
			"numero_de_bultos",
			"punto_de_llegada_ubigeo",
			"punto_de_llegada_direccion",
			"items (al menos una fila)",
			"items.unidad_de_medida",
			"items.codigo",
			"items.descripcion",
			"items.cantidad",
			"destinatario_documento_tipo (cuando tipo_de_comprobante = 8)",
			"destinatario_documento_numero (cuando tipo_de_comprobante = 8)",
			"destinatario_denominacion (cuando tipo_de_comprobante = 8)",
		];

		const selectMeanings = [
			{
				field: "tipo_de_comprobante",
				values: ["7 = GRE Remitente", "8 = GRE Transportista"],
			},
			{
				field: "estado",
				values: [
					"Borrador = No enviada",
					"Pendiente de Respuesta = Enviada, esperando SUNAT",
					"Aceptada = Aceptada por SUNAT",
					"Error = Último envío falló",
				],
			},
			{
				field: "motivo_de_traslado",
				values: [
					"01 Venta",
					"02 Compra",
					"04 Traslado entre establecimientos",
					"05 Consignación",
					"06 Devolución",
					"07 Recojo de bienes transformados",
					"08 Importación",
					"09 Exportación",
					"13 Otros",
					"14 Venta sujeta a confirmación del comprador",
					"18 Traslado emisor itinerante CP",
					"19 Traslado a zona primaria",
				],
			},
			{
				field: "tipo_de_transporte",
				values: ["01 Público", "02 Privado"],
			},
			{
				field: "peso_bruto_unidad_de_medida",
				values: ["KGM Kilogramo", "TNE Tonelada"],
			},
			{
				field: "cliente_tipo_de_documento / destinatario_documento_tipo / transportista_documento_tipo",
				values: [
					"6 RUC",
					"1 DNI",
					"4 Carnet de Extranjería",
					"7 Pasaporte",
					"A Cédula Diplomática",
					"0 No domiciliado / Otros",
				],
			},
			{
				field: "conductor_documento_tipo / conductores_secundarios.documento_tipo",
				values: ["1 DNI", "4 Carnet de Extranjería", "7 Pasaporte"],
			},
			{
				field: "formato_de_pdf",
				values: ["A4", "A5", "TICKET"],
			},
			{
				field: "documento_relacionado.tipo",
				values: ["01 Factura", "03 Boleta de Venta", "09 Guía de Remisión Remitente", "31 Guía de Remisión Transportista"],
			},
		];

		const requiredHtml = `
			<div style="margin-bottom: 12px;">
				<div style="font-weight: 600; margin-bottom: 6px;">${__("Campos obligatorios para enviar a Nubefact")}</div>
				<ul style="margin: 0; padding-left: 18px; max-height: 210px; overflow: auto;">
					${requiredFields.map((fieldname) => `<li>${frappe.utils.escape_html(fieldname)}</li>`).join("")}
				</ul>
			</div>
		`;

		const meaningsHtml = `
			<div>
				<div style="font-weight: 600; margin-bottom: 6px;">${__("Valores de campos tipo Select")}</div>
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
			title: __("Ayuda de Guía de Remisión"),
			fields: [
				{
					fieldname: "help_html",
					fieldtype: "HTML",
					options: `${requiredHtml}${meaningsHtml}`,
				},
			],
			primary_action_label: __("Cerrar"),
			primary_action: () => dialog.hide(),
		});

		dialog.show();
	},
});

function download_file_from_url(frm, fieldname, label) {
	const url = frm.doc[fieldname];

	if (!url) {
		frappe.msgprint(__("El URL de {0} todavía no está disponible.", [label]));
		return;
	}

	window.open(url, "_blank");
}
