// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const FORM_SCRIPT = "nubefact/nubefact/doctype/nubefact_migration_job/nubefact_migration_job.js";

function loadFormHandlers() {
    let handlers;
    const context = {
        __: (text) => text,
        frappe: {
            call: async () => ({}),
            msgprint() {},
            ui: {
                form: {
                    on(_doctype, registeredHandlers) {
                        handlers = registeredHandlers;
                    },
                },
            },
            user_roles: [],
        },
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(FORM_SCRIPT, "utf8"), context);
    return handlers;
}

class DashboardStub {
    constructor() {
        this.progressCharts = [];
    }

    clear_headline() {}

    add_progress(title, percent, message) {
        this.progressCharts.push({ title, percent, message });
    }

    show_progress(title, percent, message) {
        const existing = this.progressCharts.find((chart) => chart.title === title);
        if (existing) {
            Object.assign(existing, { percent, message });
        } else {
            this.progressCharts.push({ title, percent, message });
        }
    }
}

test("migration progress remains singular and current across form refreshes", () => {
    const handlers = loadFormHandlers();
    const dashboard = new DashboardStub();
    const frm = {
        dashboard,
        doc: {
            processed_count: 0,
            progress_percent: 0,
            status: "Draft",
            total_count: 5,
        },
        is_new: () => true,
    };

    handlers.refresh(frm);
    Object.assign(frm.doc, { processed_count: 2, progress_percent: 40 });
    handlers.refresh(frm);

    assert.deepEqual(dashboard.progressCharts, [
        { title: "Migración GRE", percent: 40, message: "2 / 5" },
    ]);
});
