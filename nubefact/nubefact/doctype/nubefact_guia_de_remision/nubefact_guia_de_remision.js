/* global nubefact */
// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Guia De Remision", {
    setup(frm) {
        frm.set_query("local", () => ({
            filters: frm.doc.company ? { company: frm.doc.company } : {},
        }));
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
        register_catalog_autocomplete(frm, {
            fieldname: "transportista_placa_numero",
            doctype: "Nubefact Vehiculo",
            resolve_record_name: (_frm, value) => value.trim().toUpperCase(),
            target_fields: {
                transportista_placa_numero: "placa_numero",
            },
        });
        register_catalog_autocomplete(frm, {
            fieldname: "conductor_documento_numero",
            doctype: "Nubefact Conductor",
            resolve_record_name: (currentForm, value) => {
                const documentType = currentForm.doc.conductor_documento_tipo;
                return documentType && value
                    ? `${documentType}-${value.trim().toUpperCase()}`
                    : null;
            },
            target_fields: {
                conductor_documento_tipo: "documento_tipo",
                conductor_documento_numero: "documento_numero",
                conductor_denominacion: "denominacion",
                conductor_nombre: "nombre",
                conductor_apellidos: "apellidos",
                conductor_numero_licencia: "numero_licencia",
            },
            fill_if_empty: {
                transportista_placa_numero: "vehiculo",
            },
        });
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
            frm.doc.migrated_from_nubefact ||
            [
                "Enviando",
                "Pendiente de Aceptacion",
                "Aceptada",
                "Anulación Solicitada",
                "Anulada",
            ].includes(frm.doc.status || "Borrador")
        ) {
            frm.disable_form();
        }

        setup_catalog_autocomplete(frm, "transportista_placa_numero");
        setup_catalog_autocomplete(frm, "conductor_documento_numero");

        if (!frm.is_new()) {
            const watcher = window.nubefact.get_watcher(
                frm,
                "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.refrescar_estado_sunat"
            );
            watcher.on_refresh();
            watcher.schedule_if_needed();

            if (
                !frm.doc.migrated_from_nubefact &&
                ["Borrador", "Error"].includes(frm.doc.status || "Borrador")
            ) {
                frm.add_custom_button(__("Enviar a Nubefact"), () => {
                    frm.trigger("open_send_dialog");
                });
            }

            if (!["Anulación Solicitada", "Anulada"].includes(frm.doc.status)) {
                frm.add_custom_button(__("Refrescar estado SUNAT"), async () => {
                    await watcher.refresh_now_and_continue();

                    frappe.show_alert({
                        message: __("Estado SUNAT actualizado"),
                        indicator: "green",
                    });
                });
            }

            if (frm.doc.status === "Aceptada" && frm.has_perm("write")) {
                frm.add_custom_button(__("Solicitar Anulación"), () => {
                    frm.trigger("open_void_request_dialog");
                });
            }

            const canMarkAsVoided = ["Nubefact Manager", "System Manager"].some((role) =>
                frappe.user_roles.includes(role)
            );
            if (
                frm.doc.status === "Anulación Solicitada" &&
                canMarkAsVoided &&
                frm.has_perm("write")
            ) {
                frm.add_custom_button(__("Marcar como Anulado"), () => {
                    frm.trigger("confirm_manual_void");
                });
                frm.add_custom_button(__("Cancelar Solicitud"), () => {
                    frm.trigger("open_void_reversal_dialog");
                });
            }

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
    open_void_request_dialog(frm) {
        const dialog = new frappe.ui.Dialog({
            title: __("Solicitar anulación de GRE"),
            fields: [
                {
                    fieldname: "motivo",
                    fieldtype: "Small Text",
                    label: __("Motivo de anulación"),
                    reqd: 1,
                },
            ],
            primary_action_label: __("Solicitar Anulación"),
            primary_action: async (values) => {
                await frappe.call({
                    method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.solicitar_anulacion",
                    args: {
                        name: frm.doc.name,
                        motivo: values.motivo,
                    },
                    freeze: true,
                    freeze_message: __("Registrando solicitud de anulación..."),
                });

                dialog.hide();
                await frm.reload_doc();
                frappe.show_alert({
                    message: __("Solicitud de anulación registrada"),
                    indicator: "orange",
                });
            },
        });

        dialog.show();
    },
    open_void_reversal_dialog(frm) {
        const dialog = new frappe.ui.Dialog({
            title: __("Cancelar solicitud de anulación"),
            fields: [
                {
                    fieldname: "motivo",
                    fieldtype: "Small Text",
                    label: __("Motivo de reversión"),
                    reqd: 1,
                },
            ],
            primary_action_label: __("Revertir a Aceptada"),
            primary_action: async (values) => {
                await frappe.call({
                    method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.cancelar_solicitud_de_anulacion",
                    args: {
                        name: frm.doc.name,
                        motivo: values.motivo,
                    },
                    freeze: true,
                    freeze_message: __("Revirtiendo GRE a Aceptada..."),
                });

                dialog.hide();
                await frm.reload_doc();
                frappe.show_alert({
                    message: __("Solicitud cancelada; la GRE volvió a Aceptada"),
                    indicator: "green",
                });
            },
        });

        dialog.show();
    },
    confirm_manual_void(frm) {
        frappe.confirm(
            __(
                "¿Confirmas que esta GRE ya fue anulada en el portal SUNAT? Esta acción no consulta ni modifica SUNAT."
            ),
            async () => {
                await frappe.call({
                    method: "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.marcar_como_anulada",
                    args: { name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Marcando GRE como anulada..."),
                });

                await frm.reload_doc();
                frappe.show_alert({
                    message: __("GRE marcada como anulada"),
                    indicator: "green",
                });
            }
        );
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
            "documento_relacionado_codigo (cuando motivo_de_traslado = 08 / Importación o 09 / Exportación)",
            "tipo_de_transporte",
            "peso_bruto_total",
            "peso_bruto_unidad_de_medida",
            "numero_de_bultos",
            "transportista_documento_tipo / numero / denominacion (cuando tipo_de_transporte = 01 / Público)",
            "transportista_placa_numero (transporte privado o tipo 8, excepto indicador 06 / M1L)",
            "conductor_documento_tipo / numero / nombre / apellidos / numero_licencia (transporte privado o tipo 8, excepto indicador 06 / M1L)",
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
                    "Anulación Solicitada = Pendiente de anulación manual en el portal SUNAT",
                    "Anulada = Anulación manual confirmada por un Nubefact Manager",
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

function register_catalog_autocomplete(frm, options) {
    const control = frm.fields_dict[options.fieldname];
    if (!control || control._nubefact_catalog_autocomplete) return;

    control._nubefact_catalog_autocomplete = {
        options,
        input: null,
        awesomplete: null,
        clear_button: null,
        link_controls: null,
        open_button: null,
        results: [],
    };
    const existingOnMake = control.df.on_make;
    control.df.on_make = (field) => {
        if (existingOnMake) existingOnMake(field);
        setup_catalog_autocomplete(frm, options.fieldname);
    };

    setup_catalog_autocomplete(frm, options.fieldname);
}

function setup_catalog_autocomplete(frm, fieldname) {
    const control = frm.fields_dict[fieldname];
    const state = control?._nubefact_catalog_autocomplete;
    if (!control?.$input?.length || !control.input || !state) return;
    if (state.input === control.input) {
        toggle_catalog_link_actions(control);
        return;
    }

    state.input = control.input;
    state.results = [];
    state.awesomplete = new Awesomplete(control.input, {
        tabSelect: true,
        minChars: 0,
        maxItems: 99,
        autoFirst: true,
        list: [],
        replace() {},
        data(item) {
            return {
                label: item.label || item.value,
                value: item.value,
            };
        },
        filter() {
            return true;
        },
        item(item) {
            const result =
                state.results.find((candidate) => candidate.value === item.value) ?? item;
            const label = frappe.utils.escape_html(result.label || result.value);
            const description = result.description
                ? `<br><span class="small">${frappe.utils.escape_html(result.description)}</span>`
                : "";
            return $(`<li role="option"><p><strong>${label}</strong>${description}</p></li>`)
                .data("item.autocomplete", result)
                .prop("aria-selected", "false")
                .get(0);
        },
        sort() {
            return 0;
        },
    });

    const eventNamespace = ".nubefactCatalogAutocomplete";
    const search = frappe.utils.debounce((term) => {
        search_catalog_autocomplete(frm, control, term);
    }, 300);
    setup_catalog_link_actions(frm, control, fieldname, eventNamespace);
    control.$input.off(eventNamespace);
    control.$input.on(`input${eventNamespace}`, (event) => {
        toggle_catalog_link_actions(control);
        search(event.target.value || "");
    });
    control.$input.on(`focus${eventNamespace}`, () => {
        toggle_catalog_link_actions(control);
        if (!control.$input.val()) control.$input.trigger("input");
    });
    control.$input.on(`blur${eventNamespace}`, () => {
        setTimeout(() => state.link_controls?.toggle(false), 250);
    });
    control.$input.on(`awesomplete-select${eventNamespace}`, (event) => {
        const selectedName = event.originalEvent?.text?.value;
        if (!selectedName) return;

        event.preventDefault();
        state.awesomplete.close();
        return apply_catalog_selection(frm, state.options, selectedName).then(() => {
            toggle_catalog_link_actions(control);
        });
    });
}

function setup_catalog_link_actions(frm, control, fieldname, eventNamespace) {
    const state = control._nubefact_catalog_autocomplete;
    const $inputArea = control.$wrapper.find(".control-input");
    state.link_controls = $('<span class="link-btn nubefact-catalog-actions"></span>')
        .toggle(false)
        .appendTo($inputArea);
    state.clear_button = $(
        `<a class="btn-clear" title="${__("Clear")}">
            ${frappe.utils.icon("close", "xs", "es-icon")}
        </a>`
    )
        .on("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (!control.can_write()) return;

            await frm.set_value(fieldname, null);
            control.$input.focus().trigger("input");
        })
        .appendTo(state.link_controls);
    state.open_button = $(
        `<a class="btn-open" tabindex="-1" title="${__("Open Link")}">
            ${frappe.utils.icon("arrow-right", "xs")}
        </a>`
    )
        .on("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            await open_catalog_record(frm, state.options, control.$input.val());
        })
        .appendTo(state.link_controls);

    $inputArea.off(eventNamespace);
    $inputArea.on(`mouseenter${eventNamespace}`, () => toggle_catalog_link_actions(control));
    $inputArea.on(`mouseleave${eventNamespace}`, () => {
        if (!control.$input.is(":focus")) state.link_controls.toggle(false);
    });
}

function toggle_catalog_link_actions(control) {
    const state = control._nubefact_catalog_autocomplete;
    state.link_controls?.toggle(Boolean(control.$input.val()) && control.can_write());
}

async function open_catalog_record(frm, options, value) {
    const recordName = options.resolve_record_name(frm, value || "");
    const { message } = recordName
        ? await frappe.db.get_value(options.doctype, recordName, "name")
        : { message: null };
    if (!message?.name) {
        frappe.msgprint({
            title: __("Registro no encontrado"),
            message: __("No existe un registro de {0} para la clave {1}.", [
                __(options.doctype),
                frappe.utils.escape_html(recordName || value || __("vacía")),
            ]),
            indicator: "orange",
        });
        return;
    }

    frappe.set_route("Form", options.doctype, recordName);
}

function search_catalog_autocomplete(frm, control, term) {
    const state = control._nubefact_catalog_autocomplete;
    const input = control.input;
    frappe.call({
        type: "POST",
        method: "frappe.desk.search.search_link",
        no_spinner: true,
        args: {
            txt: term,
            doctype: state.options.doctype,
            reference_doctype: frm.doctype,
            page_length: frappe.boot.sysdefaults?.link_field_results_limit || 10,
        },
        callback: (response) => {
            if (state.input !== input || control.$input.val() !== term) return;

            state.results = response.message || [];
            state.awesomplete.list = state.results;
        },
    });
}

async function apply_catalog_selection(frm, options, selectedName) {
    const fillIfEmpty = options.fill_if_empty ?? {};
    const sourceFields = [
        ...new Set([...Object.values(options.target_fields), ...Object.values(fillIfEmpty)]),
    ];
    const { message } = await frappe.db.get_value(options.doctype, selectedName, sourceFields);
    if (!message) {
        frappe.msgprint(__("El registro seleccionado ya no existe."));
        return;
    }

    const targetValues = {};
    for (const [targetField, sourceField] of Object.entries(options.target_fields)) {
        targetValues[targetField] = message[sourceField] ?? null;
    }
    for (const [targetField, sourceField] of Object.entries(fillIfEmpty)) {
        if (!frm.doc[targetField] && message[sourceField]) {
            targetValues[targetField] = message[sourceField];
        }
    }
    await frm.set_value(targetValues);
}

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
