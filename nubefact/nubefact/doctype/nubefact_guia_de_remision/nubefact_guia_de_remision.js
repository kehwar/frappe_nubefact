/* global nubefact */
// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Guia De Remision", {
    setup(frm) {
        frm.set_query("nubefact_series", () => ({
            filters: {
                ...(frm.doc.tipo_de_comprobante
                    ? { tipo_de_comprobante: frm.doc.tipo_de_comprobante }
                    : {}),
                ...(frm.doc.company ? { company: frm.doc.company } : {}),
                ...(frm.doc.local ? { local: frm.doc.local } : {}),
            },
        }));
        frm.set_query("tipo_de_comprobante", () => ({
            filters: { aplica_guia_de_remision: 1 },
        }));
        for (const fieldname of [
            "cliente_tipo_de_documento",
            "destinatario_documento_tipo",
            "pagador_servicio_documento_tipo_identidad",
        ]) {
            frm.set_query(fieldname, () => ({
                filters: { aplica_guia_de_remision: 1 },
            }));
        }
        for (const fieldname of [
            "transportista_documento_tipo",
            "subcontratador_documento_tipo",
        ]) {
            frm.set_query(fieldname, () => ({
                filters: { aplica_transportista: 1 },
            }));
        }
        frm.set_query("conductor_documento_tipo", () => ({
            filters: { aplica_conductor: 1 },
        }));
        frm.set_query("documento_tipo", "conductores_secundarios", () => ({
            filters: { aplica_conductor: 1 },
        }));
        frm.set_query("peso_bruto_unidad_de_medida", () => ({
            filters: { aplica_peso_bruto: 1 },
        }));
        frm.set_query("sunat_envio_indicador", () => ({
            filters:
                frm.doc.tipo_de_comprobante === "7"
                    ? { aplica_gre_remitente: 1 }
                    : { aplica_gre_transportista: 1 },
        }));
    },
    async nubefact_series(frm) {
        const requestedSeries = frm.doc.nubefact_series;
        if (!requestedSeries) return;

        const { message } = await frappe.db.get_value("Nubefact Series", requestedSeries, [
            "company",
            "local",
            "tipo_de_comprobante",
            "serie",
        ]);
        if (message && frm.doc.nubefact_series === requestedSeries) {
            await frm.set_value(message);
        }
    },
    refresh(frm) {
        frm.set_intro(format_error_message_banner(frm.doc.error_message), "red");

        if (
            ["Enviando", "Pendiente de Aceptacion", "Aceptada"].includes(
                frm.doc.status || "Borrador"
            )
        ) {
            frm.disable_form();
        }

        if (!frm.is_new()) {
            const watcher = window.nubefact.get_watcher(
                frm,
                "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.refrescar_estado_sunat"
            );
            watcher.on_refresh();
            watcher.schedule_if_needed();

            if (["Borrador", "Error"].includes(frm.doc.status || "Borrador")) {
                frm.add_custom_button(__("Enviar a Nubefact"), () => {
                    frm.trigger("open_send_dialog");
                });
            }

            frm.add_custom_button(__("Refrescar estado SUNAT"), async () => {
                await watcher.refresh_now_and_continue();

                frappe.show_alert({
                    message: __("Estado SUNAT actualizado"),
                    indicator: "green",
                });
            });

            if (frm.doc.enlace_del_pdf) {
                frm.add_custom_button(
                    __("PDF"),
                    () => {
                        download_file_from_url(frm, "enlace_del_pdf", "PDF");
                    },
                    "Descargar"
                );
            }

            if (frm.doc.enlace_del_xml) {
                frm.add_custom_button(
                    __("XML"),
                    () => {
                        download_file_from_url(frm, "enlace_del_xml", "XML");
                    },
                    "Descargar"
                );
            }

            if (frm.doc.enlace_del_cdr) {
                frm.add_custom_button(
                    __("CDR"),
                    () => {
                        download_file_from_url(frm, "enlace_del_cdr", "CDR");
                    },
                    "Descargar"
                );
            }
        }

        frm.add_custom_button(__("Ayuda"), () => {
            frm.trigger("open_help_dialog");
        });
    },
    open_send_dialog(frm) {
        frappe.confirm(__("¿Confirmas enviar esta Guía de Remisión a Nubefact?"), async () => {
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

            const has_error = message?.status === "Error";
            frappe.show_alert({
                message: has_error
                    ? __("Falló el envío de la guía. El estado cambió a Error")
                    : __("Guía de Remisión enviada a Nubefact"),
                indicator: has_error ? "red" : "green",
            });
        });
    },
    open_help_dialog(frm) {
        const requiredFields = [
            "tipo_de_comprobante",
            "nubefact_series",
            "serie (desde Serie NubeFact)",
            "numero (asignado al emitir)",
            "fecha_de_emision",
            "fecha_de_inicio_de_traslado",
            "fecha_de_entrega_al_transportista (tipo 7 con transporte público)",
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
                field: "status",
                values: [
                    "Borrador = No enviada",
                    "Pendiente de Aceptacion = Enviada, esperando SUNAT",
                    "Aceptada = Aceptada por SUNAT",
                    "Error = Último envío falló",
                ],
            },
            {
                field: "motivo_de_traslado",
                values: [
                    "01 Venta",
                    "02 Compra",
                    "03 Venta con entrega a terceros",
                    "04 Traslado entre establecimientos",
                    "05 Consignación",
                    "06 Devolución",
                    "07 Recojo de bienes transformados",
                    "08 Importación",
                    "09 Exportación",
                    "13 Otros",
                    "14 Venta sujeta a confirmación del comprador",
                    "17 Traslado de bienes para transformación",
                    "18 Traslado emisor itinerante CP",
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
                field: "cliente_tipo_de_documento / destinatario_documento_tipo",
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
                values: [
                    "1 DNI",
                    "4 Carnet de Extranjería",
                    "7 Pasaporte",
                    "A Cédula Diplomática",
                    "0 No domiciliado / Otros",
                ],
            },
            {
                field: "formato_de_pdf",
                values: ["A4", "TICKET"],
            },
            {
                field: "documento_relacionado.tipo",
                values: [
                    "01 Factura",
                    "03 Boleta de Venta",
                    "09 Guía de Remisión Remitente",
                    "31 Guía de Remisión Transportista",
                ],
            },
        ];

        const requiredHtml = `
			<div style="margin-bottom: 12px;">
				<div style="font-weight: 600; margin-bottom: 6px;">${__(
                    "Campos obligatorios para enviar a Nubefact"
                )}</div>
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

function format_error_message_banner(errorMessage) {
    const sanitizedMessage = frappe.utils.escape_html((errorMessage || "").trim());
    if (!sanitizedMessage) {
        return "";
    }

    return sanitizedMessage.replace(/\r?\n/g, "<br>");
}

function download_file_from_url(frm, fieldname, label) {
    const url = frm.doc[fieldname];

    if (!url) {
        frappe.msgprint(__("El URL de {0} todavía no está disponible.", [label]));
        return;
    }

    window.open(url, "_blank");
}
