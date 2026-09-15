// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const WATCHER_SCRIPT = "nubefact/public/js/nubefact.bundle.js";
const SYSTEM_DATETIME = "2026-09-15 12:00:00";
const RECENT_CREATION = "2026-09-15 11:00:00.000000";

function loadWatcher() {
    const context = {
        console,
        cur_page: null,
        __(message) {
            return message;
        },
        frappe: {
            async call() {
                context.apiCalls += 1;
            },
            datetime: {
                system_datetime() {
                    return SYSTEM_DATETIME;
                },
            },
            provide() {
                context.nubefact = context.nubefact || {};
            },
        },
        apiCalls: 0,
        setTimeout,
        clearTimeout,
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(WATCHER_SCRIPT, "utf8"), context);
    return context;
}

function needsSunatRefresh(doc) {
    const context = loadWatcher();
    const watcher = new context.nubefact.Watcher({ doc }, "test.method");
    return watcher.needs_sunat_refresh();
}

test("pending documents continue polling even when all artifact links exist", () => {
    for (const status of ["Pendiente de Aceptación", "Pendiente de Aceptacion"]) {
        assert.equal(
            needsSunatRefresh({
                status,
                creation: RECENT_CREATION,
                enlace_del_pdf: "https://files.example.test/document.pdf",
                enlace_del_xml: "https://files.example.test/document.xml",
                enlace_del_cdr: "https://files.example.test/document.cdr",
            }),
            true,
            status
        );
    }
});

test("accepted documents continue polling while any artifact link is missing", () => {
    for (const missingField of ["enlace_del_pdf", "enlace_del_xml", "enlace_del_cdr"]) {
        const doc = {
            status: "Aceptada",
            creation: RECENT_CREATION,
            enlace_del_pdf: "https://files.example.test/document.pdf",
            enlace_del_xml: "https://files.example.test/document.xml",
            enlace_del_cdr: "https://files.example.test/document.cdr",
        };
        doc[missingField] = "";

        assert.equal(needsSunatRefresh(doc), true, missingField);
    }
});

test("accepted documents stop polling after all artifact links exist", () => {
    assert.equal(
        needsSunatRefresh({
            status: "Aceptada",
            creation: RECENT_CREATION,
            enlace_del_pdf: "https://files.example.test/document.pdf",
            enlace_del_xml: "https://files.example.test/document.xml",
            enlace_del_cdr: "https://files.example.test/document.cdr",
        }),
        false
    );
});

test("automatic polling stops exactly 24 hours after document creation", () => {
    for (const status of ["Pendiente de Aceptación", "Pendiente de Aceptacion", "Aceptada"]) {
        assert.equal(
            needsSunatRefresh({
                status,
                creation: "2026-09-14 12:00:00.000000",
                enlace_del_pdf: "",
                enlace_del_xml: "",
                enlace_del_cdr: "",
            }),
            false,
            status
        );
    }
});

test("manual refresh remains available after the automatic cutoff", async () => {
    const context = loadWatcher();
    const frm = {
        doc: {
            name: "GRE-OLD",
            status: "Aceptada",
            creation: "2026-09-14 11:59:59.000000",
        },
        async reload_doc() {},
        is_dirty() {
            return false;
        },
    };
    const watcher = new context.nubefact.Watcher(frm, "test.method");

    await watcher.refresh_now_and_continue({ freeze: false });

    assert.equal(context.apiCalls, 1);
});

test("documents outside the pending and accepted states do not poll for artifacts", () => {
    assert.equal(needsSunatRefresh({ status: "Error", creation: RECENT_CREATION }), false);
});
