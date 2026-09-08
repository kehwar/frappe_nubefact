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
        __: (text) => text,
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
            utils: {
                escape_html(value) {
                    return String(value)
                        .replaceAll("&", "&amp;")
                        .replaceAll('"', "&quot;")
                        .replaceAll("<", "&lt;")
                        .replaceAll(">", "&gt;");
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

test("artifact shortcuts prefer downloaded GRE files over NubeFact URLs", () => {
    const loaded = loadAttachmentListener();
    const frm = {
        doc: {
            tipo_de_comprobante: "7",
            serie: "TTT1",
            numero: 42,
            enlace_del_pdf: "https://nubefact.test/document.pdf",
            enlace_del_xml: "https://nubefact.test/document.xml",
            enlace_del_cdr: "https://nubefact.test/cdr.xml",
        },
        get_docinfo: () => ({
            attachments: [
                {
                    file_name: "unrelated.pdf",
                    file_url: "/private/files/unrelated.pdf",
                    is_private: 1,
                },
                {
                    file_name: "20506005133-09-TTT1-00000042.pdf",
                    file_url: "/private/files/20506005133-09-TTT1-00000042.pdf",
                    is_private: 1,
                },
                {
                    file_name: "20506005133-09-TTT1-00000042-xml-field.zip",
                    file_url: "/private/files/20506005133-09-TTT1-00000042-xml-field.zip",
                    is_private: 1,
                },
                {
                    file_name: "R-20506005133-09-TTT1-00000042.xml",
                    file_url: "/private/files/R-20506005133-09-TTT1-00000042.xml",
                    is_private: 1,
                },
            ],
        }),
    };

    const html = loaded.context.build_artifact_shortcut_links(frm);

    assert.match(html, /Ver PDF 📄/);
    assert.match(html, /Descargar XML 📥/);
    assert.match(html, /CDR ✅/);
    assert.match(html, /href="\/private\/files\/20506005133-09-TTT1-00000042\.pdf"/);
    assert.match(html, /href="\/private\/files\/20506005133-09-TTT1-00000042-xml-field\.zip"/);
    assert.match(html, /href="\/private\/files\/R-20506005133-09-TTT1-00000042\.xml"/);
    assert.doesNotMatch(html, /nubefact\.test/);
    assert.doesNotMatch(html, /unrelated\.pdf/);
});

test("artifact shortcuts fall back to safe NubeFact URLs", () => {
    const loaded = loadAttachmentListener();
    const frm = {
        doc: {
            tipo_de_comprobante: "8",
            serie: "V001",
            numero: 7,
            enlace_del_pdf: "https://nubefact.test/document.pdf?token=one&view=true",
            enlace_del_xml: "https://nubefact.test/document.xml",
            enlace_del_cdr: "javascript:alert(1)",
        },
        get_docinfo: () => ({ attachments: [] }),
    };

    const html = loaded.context.build_artifact_shortcut_links(frm);

    assert.match(
        html,
        /href="https:\/\/nubefact\.test\/document\.pdf\?token=one&amp;view=true"[^>]*>Ver PDF 📄<\/a>/
    );
    assert.match(html, /href="https:\/\/nubefact\.test\/document\.xml"[^>]* download>/);
    assert.doesNotMatch(html, /CDR ✅/);
    assert.equal((html.match(/aria-hidden="true"/g) || []).length, 1);
});

test("the shortcut headline preserves and escapes the GRE error message", () => {
    const loaded = loadAttachmentListener();
    let intro;
    const frm = {
        doc: {
            tipo_de_comprobante: "7",
            serie: "TTT1",
            numero: 1,
            enlace_del_pdf: "https://nubefact.test/document.pdf",
            error_message: "Falló <script>alert(1)</script>",
        },
        get_docinfo: () => ({ attachments: [] }),
        set_intro(html, color) {
            intro = { html, color };
        },
    };

    loaded.context.render_artifact_shortcuts(frm);

    assert.equal(intro.color, "red");
    assert.match(intro.html, /Ver PDF 📄/);
    assert.match(intro.html, /Falló &lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.doesNotMatch(intro.html, /<script>/);
});
