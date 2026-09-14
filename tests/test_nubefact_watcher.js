// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const WATCHER_SCRIPT = "nubefact/public/js/nubefact.bundle.js";

function loadWatcher() {
    const context = {
        console,
        frappe: {
            provide() {
                context.nubefact = context.nubefact || {};
            },
        },
        setTimeout,
        clearTimeout,
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(WATCHER_SCRIPT, "utf8"), context);
    return context.nubefact.Watcher;
}

function needsSunatRefresh(doc) {
    const Watcher = loadWatcher();
    const watcher = new Watcher({ doc }, "test.method");
    return watcher.needs_sunat_refresh();
}

test("pending documents continue polling even when all artifact links exist", () => {
    for (const status of ["Pendiente de Aceptación", "Pendiente de Aceptacion"]) {
        assert.equal(
            needsSunatRefresh({
                status,
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
            enlace_del_pdf: "https://files.example.test/document.pdf",
            enlace_del_xml: "https://files.example.test/document.xml",
            enlace_del_cdr: "https://files.example.test/document.cdr",
        }),
        false
    );
});

test("documents outside the pending and accepted states do not poll for artifacts", () => {
    assert.equal(needsSunatRefresh({ status: "Error" }), false);
});
