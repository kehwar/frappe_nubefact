// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Conductor", {
    setup(frm) {
        frm.set_query("documento_tipo", () => ({
            filters: { aplica_conductor: 1 },
        }));
    },
});
