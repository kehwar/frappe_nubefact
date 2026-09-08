// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Migration Job", {
    setup(frm) {
        frm.set_query("local", () => ({
            filters: frm.doc.company ? { company: frm.doc.company } : {},
        }));
        frm.set_query("nubefact_series", () => ({
            filters: {
                tipo_de_comprobante: "7",
                ...(frm.doc.company ? { company: frm.doc.company } : {}),
                ...(frm.doc.local ? { local: frm.doc.local } : {}),
            },
        }));
    },
    refresh(frm) {
        const active = [
            "Queued",
            "Querying",
            "Waiting for Artifacts",
            "Downloading",
            "Recreating",
        ];
        const manager = ["Nubefact Manager", "System Manager"].some((role) =>
            frappe.user_roles.includes(role)
        );
        frm.dashboard.clear_headline();
        frm.dashboard.show_progress(
            __("Migración GRE"),
            frm.doc.progress_percent || 0,
            `${frm.doc.processed_count || 0} / ${frm.doc.total_count || 0}`
        );

        if (!frm.is_new() && manager && frm.doc.status === "Draft") {
            frm.add_custom_button(__("Iniciar migración"), async () => {
                if (frm.is_dirty()) await frm.save();
                await migration_call(frm, "start_migration");
            });
        }
        if (!frm.is_new() && manager && active.includes(frm.doc.status)) {
            frm.add_custom_button(__("Cancelar"), async () => {
                await migration_call(frm, "cancel_migration");
            });
        }
        if (!frm.is_new() && manager && frm.doc.status === "Cancelled") {
            frm.add_custom_button(__("Reanudar migración"), async () => {
                await migration_call(frm, "retry_migration");
            });
        }
        if (!frm.is_new() && manager && (frm.doc.failed_count || 0) > 0) {
            frm.add_custom_button(
                __("Reintentar fallidos"),
                async () => {
                    await migration_call(frm, "retry_migration");
                },
                __("Reintentar")
            );
        }
        if (!frm.is_new() && manager && (frm.doc.warning_count || 0) > 0) {
            frm.add_custom_button(
                __("Reintentar artefactos faltantes"),
                async () => {
                    await migration_call(frm, "retry_migration", { include_warnings: 1 });
                },
                __("Reintentar")
            );
        }
        if (!frm.is_new() && manager && !active.includes(frm.doc.status)) {
            frm.add_custom_button(
                __("Reintentar números seleccionados"),
                async () => {
                    const selected = frm.fields_dict.results.grid
                        .get_selected_children()
                        .filter((row) => ["Failed", "Warning", "Not Found"].includes(row.status))
                        .map((row) => row.number);
                    if (!selected.length) {
                        frappe.msgprint(__("Seleccione resultados Failed, Warning o Not Found."));
                        return;
                    }
                    await migration_call(frm, "retry_migration", { numbers: selected });
                },
                __("Reintentar")
            );
        }
        if (!frm.is_new() && manager && (frm.doc.not_found_count || 0) > 0) {
            frm.add_custom_button(
                __("Reintentar no encontrados"),
                async () => {
                    await migration_call(frm, "retry_migration", { include_not_found: 1 });
                },
                __("Reintentar")
            );
        }
    },
});

async function migration_call(frm, action, extraArgs = {}) {
    await frappe.call({
        method: `nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job.${action}`,
        args: { job_name: frm.doc.name, ...extraArgs },
        freeze: true,
        freeze_message: __("Actualizando migración..."),
    });
    await frm.reload_doc();
}
