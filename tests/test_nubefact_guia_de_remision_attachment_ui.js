// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const FORM_SCRIPT =
    "nubefact/nubefact/doctype/nubefact_guia_de_remision/nubefact_guia_de_remision.js";

function loadAttachmentListener() {
    let listener;
    let registrations = 0;
    const context = {
        frappe: {
            realtime: {
                on(event, callback) {
                    assert.equal(event, "nubefact_attachments_ready");
                    listener = callback;
                    registrations += 1;
                },
            },
            ui: {
                form: {
                    on() {},
                },
            },
        },
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(FORM_SCRIPT, "utf8"), context);
    context.setup_attachment_completion_listener();
    context.setup_attachment_completion_listener();

    return {
        context,
        getListener: () => listener,
        getRegistrations: () => registrations,
    };
}

function setCurrentForm(loaded, { docname = "GRE-0001", isDirty = () => false, reload }) {
    const frm = {
        doctype: "Nubefact Guia De Remision",
        docname,
        is_dirty: isDirty,
        reload_doc: reload,
    };
    loaded.context.cur_page = { page: { frm } };
    return frm;
}

test("the open GRE reloads once when its complete attachment batch arrives", async () => {
    const loaded = loadAttachmentListener();
    let reloads = 0;
    setCurrentForm(loaded, {
        async reload() {
            reloads += 1;
        },
    });

    await loaded.getListener()({
        doctype: "Nubefact Guia De Remision",
        name: "GRE-0001",
    });

    assert.equal(loaded.getRegistrations(), 1);
    assert.equal(reloads, 1);
});

test("attachment completion for another document does not reload the open GRE", async () => {
    const loaded = loadAttachmentListener();
    let reloads = 0;
    setCurrentForm(loaded, {
        async reload() {
            reloads += 1;
        },
    });

    await loaded.getListener()({
        doctype: "Nubefact Guia De Remision",
        name: "GRE-0002",
    });

    assert.equal(reloads, 0);
});

test("an attachment event received during reload queues one follow-up reload", async () => {
    const loaded = loadAttachmentListener();
    let releaseFirstReload;
    let reloads = 0;
    const firstReload = new Promise((resolve) => {
        releaseFirstReload = resolve;
    });
    setCurrentForm(loaded, {
        async reload() {
            reloads += 1;
            if (reloads === 1) await firstReload;
        },
    });

    const firstEvent = loaded.getListener()({
        doctype: "Nubefact Guia De Remision",
        name: "GRE-0001",
    });
    await Promise.resolve();
    await loaded.getListener()({
        doctype: "Nubefact Guia De Remision",
        name: "GRE-0001",
    });
    releaseFirstReload();
    await firstEvent;

    assert.equal(reloads, 2);
});

test("a dirty GRE defers its attachment reload until the form becomes clean", async () => {
    const loaded = loadAttachmentListener();
    let dirty = true;
    let reloads = 0;
    const frm = setCurrentForm(loaded, {
        isDirty: () => dirty,
        async reload() {
            reloads += 1;
        },
    });

    await loaded.getListener()({
        doctype: "Nubefact Guia De Remision",
        name: "GRE-0001",
    });
    assert.equal(reloads, 0);

    dirty = false;
    await loaded.context.reload_completed_attachment_batches(frm);
    assert.equal(reloads, 1);
});
