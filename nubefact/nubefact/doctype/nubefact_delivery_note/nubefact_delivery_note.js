// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nubefact Delivery Note", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		frm.add_custom_button(__("Refresh SUNAT Status"), async () => {
			await frappe.call({
				method: "nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note.refresh_sunat_status",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Refreshing SUNAT status..."),
			});

			await frm.reload_doc();
			frappe.show_alert({
				message: __("SUNAT status refreshed"),
				indicator: "green",
			});
		}, __("Actions"));
	},
});
