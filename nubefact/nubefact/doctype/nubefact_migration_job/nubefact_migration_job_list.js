// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Nubefact Migration Job"] = {
    onload(listview) {
        if (
            !["Nubefact Manager", "System Manager"].some((role) =>
                frappe.user_roles.includes(role)
            )
        ) {
            return;
        }
        listview.page.set_primary_action(__("Nueva migración GRE Remitente"), () => {
            open_migration_dialog();
        });
    },
    get_indicator(doc) {
        const colors = {
            Draft: "gray",
            Cancelled: "gray",
            Queued: "blue",
            Querying: "blue",
            "Waiting for Artifacts": "blue",
            Downloading: "blue",
            Recreating: "blue",
            Completed: "green",
            "Completed with Warnings": "orange",
            Failed: "red",
        };
        return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
    },
};

function open_migration_dialog() {
    const dialog = new frappe.ui.Dialog({
        title: __("Nueva migración GRE Remitente"),
        fields: [
            {
                fieldname: "company",
                fieldtype: "Link",
                label: __("Compañía"),
                options: "Company",
                reqd: 1,
            },
            {
                fieldname: "local",
                fieldtype: "Link",
                label: __("Local"),
                options: "Nubefact Local",
                reqd: 1,
            },
            {
                fieldname: "nubefact_series",
                fieldtype: "Link",
                label: __("Serie NubeFact"),
                options: "Nubefact Series",
                reqd: 1,
            },
            { fieldname: "from_number", fieldtype: "Int", label: __("Desde Número"), reqd: 1 },
            { fieldname: "to_number", fieldtype: "Int", label: __("Hasta Número"), reqd: 1 },
        ],
        primary_action_label: __("Crear e iniciar"),
        primary_action: async (values) => {
            const { message: jobName } = await frappe.call({
                method: "nubefact.nubefact.doctype.nubefact_migration_job.nubefact_migration_job.create_and_start_migration",
                args: values,
                freeze: true,
                freeze_message: __("Creando migración..."),
            });
            dialog.hide();
            frappe.set_route("Form", "Nubefact Migration Job", jobName);
        },
    });
    dialog.fields_dict.local.get_query = () => ({
        filters: dialog.get_value("company") ? { company: dialog.get_value("company") } : {},
    });
    dialog.fields_dict.nubefact_series.get_query = () => ({
        filters: {
            tipo_de_comprobante: "7",
            ...(dialog.get_value("company") ? { company: dialog.get_value("company") } : {}),
            ...(dialog.get_value("local") ? { local: dialog.get_value("local") } : {}),
        },
    });
    dialog.show();
}
