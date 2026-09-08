// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const FORM_SCRIPT =
    "nubefact/nubefact/doctype/nubefact_guia_de_remision/nubefact_guia_de_remision.js";

function loadFormHandlers(getValue) {
    let handlers;
    let lastDialog;

    class DialogStub {
        constructor(options) {
            this.options = options;
            this.hidden = false;
            this.shown = false;
            lastDialog = this;
        }

        hide() {
            this.hidden = true;
        }

        show() {
            this.shown = true;
        }
    }

    const context = {
        __: (text) => text,
        frappe: {
            db: { get_value: getValue },
            msgprint() {},
            show_alert() {},
            ui: {
                Dialog: DialogStub,
                form: {
                    on(_doctype, registeredHandlers) {
                        handlers = registeredHandlers;
                    },
                },
            },
        },
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(FORM_SCRIPT, "utf8"), context);
    return { getDialog: () => lastDialog, handlers };
}

function makeForm(initialValues = {}) {
    let assignedValues;
    const doc = { ...initialValues };
    return {
        frm: {
            doc,
            async set_value(values) {
                assignedValues = values;
                Object.assign(doc, values);
            },
        },
        getAssignedValues: () => ({ ...assignedValues }),
    };
}

test("vehicle catalog selection copies the plate to the unchanged GRE field", async () => {
    let request;
    const loaded = loadFormHandlers(async (doctype, name, fields) => {
        request = { doctype, fields: Array.from(fields), name };
        return { message: { placa_numero: "ABC123" } };
    });
    const { frm, getAssignedValues } = makeForm();

    loaded.handlers.open_vehicle_catalog_dialog(frm);
    const dialog = loaded.getDialog();
    assert.equal(dialog.shown, true);
    assert.equal(dialog.options.fields[0].options, "Nubefact Vehiculo");

    await dialog.options.primary_action({ vehiculo: "ABC123" });

    assert.deepEqual(request, {
        doctype: "Nubefact Vehiculo",
        fields: ["placa_numero"],
        name: "ABC123",
    });
    assert.deepEqual(getAssignedValues(), { transportista_placa_numero: "ABC123" });
    assert.equal(dialog.hidden, true);
});

test("driver catalog selection copies every conductor field to the GRE", async () => {
    const catalogValues = {
        documento_tipo: "1",
        documento_numero: "12345678",
        denominacion: null,
        nombre: "JUAN",
        apellidos: "PEREZ",
        numero_licencia: "Q12345678",
        vehiculo: "ABC123",
    };
    let requestedFields;
    const loaded = loadFormHandlers(async (_doctype, _name, fields) => {
        requestedFields = Array.from(fields);
        return { message: catalogValues };
    });
    const { frm, getAssignedValues } = makeForm();

    loaded.handlers.open_driver_catalog_dialog(frm);
    const dialog = loaded.getDialog();
    assert.equal(dialog.options.fields[0].options, "Nubefact Conductor");

    await dialog.options.primary_action({ conductor: "1-12345678" });

    assert.deepEqual(requestedFields, [
        "documento_tipo",
        "documento_numero",
        "denominacion",
        "nombre",
        "apellidos",
        "numero_licencia",
        "vehiculo",
    ]);
    assert.deepEqual(getAssignedValues(), {
        conductor_documento_tipo: "1",
        conductor_documento_numero: "12345678",
        conductor_denominacion: null,
        conductor_nombre: "JUAN",
        conductor_apellidos: "PEREZ",
        conductor_numero_licencia: "Q12345678",
        transportista_placa_numero: "ABC123",
    });
    assert.equal(dialog.hidden, true);
});

test("driver catalog selection does not replace an existing GRE plate", async () => {
    const loaded = loadFormHandlers(async () => ({
        message: {
            documento_tipo: "1",
            documento_numero: "12345678",
            denominacion: null,
            nombre: "JUAN",
            apellidos: "PEREZ",
            numero_licencia: "Q12345678",
            vehiculo: "NEW123",
        },
    }));
    const { frm, getAssignedValues } = makeForm({ transportista_placa_numero: "OLD123" });

    loaded.handlers.open_driver_catalog_dialog(frm);
    await loaded.getDialog().options.primary_action({ conductor: "1-12345678" });

    assert.equal(getAssignedValues().transportista_placa_numero, undefined);
    assert.equal(frm.doc.transportista_placa_numero, "OLD123");
});
