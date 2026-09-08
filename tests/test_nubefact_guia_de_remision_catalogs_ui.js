// Copyright (c) 2026, Erick W.R. and Contributors
// See license.txt

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const FORM_SCRIPT =
    "nubefact/nubefact/doctype/nubefact_guia_de_remision/nubefact_guia_de_remision.js";

function makeJqueryElement() {
    const handlers = {};
    return {
        children: [],
        handlers,
        visible: true,
        appendTo(parent) {
            parent.children.push(this);
            return this;
        },
        data() {
            return this;
        },
        get() {
            return {};
        },
        off(namespace) {
            for (const eventName of Object.keys(handlers)) {
                if (eventName.endsWith(namespace)) delete handlers[eventName];
            }
            return this;
        },
        on(eventName, handler) {
            handlers[eventName] = handler;
            return this;
        },
        prop() {
            return this;
        },
        toggle(visible) {
            this.visible = visible;
            return this;
        },
    };
}

function makeInput(initialValue = "") {
    const input = { value: initialValue };
    const $input = makeJqueryElement();
    $input.length = 1;
    $input.focused = false;
    $input.focus = function () {
        this.focused = true;
        this.trigger("focus");
        return this;
    };
    $input.is = function (selector) {
        return selector === ":focus" && this.focused;
    };
    $input.trigger = function (eventType) {
        const eventName = Object.keys(this.handlers).find((name) =>
            name.startsWith(`${eventType}.`)
        );
        return this.handlers[eventName]?.({ target: input });
    };
    $input.val = function (value) {
        if (arguments.length) {
            input.value = value;
            return this;
        }
        return input.value;
    };
    return { $input, handlers: $input.handlers, input };
}

function makeControl() {
    const input = makeInput();
    const inputArea = makeJqueryElement();
    return {
        ...input,
        inputArea,
        control: {
            $input: input.$input,
            $wrapper: {
                find(selector) {
                    assert.equal(selector, ".control-input");
                    return inputArea;
                },
            },
            can_write: () => true,
            df: {},
            input: input.input,
        },
    };
}

function loadFormScript({ call, getValue, msgprint = () => {}, setRoute = () => {} }) {
    let handlers;
    const autocompleteInstances = [];

    class AwesompleteStub {
        constructor(input, options) {
            this.input = input;
            this.options = options;
            this.list = options.list;
            this.closed = false;
            autocompleteInstances.push(this);
        }

        close() {
            this.closed = true;
        }
    }

    const context = {
        $: () => makeJqueryElement(),
        Awesomplete: AwesompleteStub,
        __: (text, values = []) =>
            values.reduce((message, value, index) => message.replace(`{${index}}`, value), text),
        frappe: {
            boot: { sysdefaults: { link_field_results_limit: 12 } },
            call,
            db: { get_value: getValue },
            msgprint,
            set_route: setRoute,
            show_alert() {},
            ui: {
                form: {
                    on(_doctype, registeredHandlers) {
                        handlers = registeredHandlers;
                    },
                },
            },
            utils: {
                debounce: (callback) => callback,
                escape_html: (value) => value,
                icon: () => "<svg></svg>",
            },
        },
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(FORM_SCRIPT, "utf8"), context);
    return { autocompleteInstances, context, handlers };
}

function makeForm(initialValues = {}) {
    let assignedValues;
    const doc = { ...initialValues };
    const vehicle = makeControl();
    const driver = makeControl();
    const frm = {
        doctype: "Nubefact Guia De Remision",
        doc,
        fields_dict: {
            conductor_documento_numero: driver.control,
            transportista_placa_numero: vehicle.control,
        },
        set_query() {},
        async set_value(fieldname, value) {
            const values =
                typeof fieldname === "string" ? { [fieldname]: value } : { ...fieldname };
            assignedValues = values;
            Object.assign(doc, values);
            if (Object.hasOwn(values, "transportista_placa_numero")) {
                vehicle.input.value = values.transportista_placa_numero || "";
            }
            if (Object.hasOwn(values, "conductor_documento_numero")) {
                driver.input.value = values.conductor_documento_numero || "";
            }
        },
    };
    return {
        controls: { driver, vehicle },
        frm,
        getAssignedValues: () => ({ ...assignedValues }),
    };
}

function autocompleteSelectHandler(control) {
    return control.handlers["awesomplete-select.nubefactCatalogAutocomplete"];
}

test("existing GRE Data inputs are enhanced with catalog autocomplete", () => {
    let searchRequest;
    const loaded = loadFormScript({
        call(options) {
            searchRequest = options;
            options.callback({
                message: [{ value: "ABC123", label: "Camión principal", description: "ABC123" }],
            });
        },
        getValue: async () => ({ message: null }),
    });
    const { controls, frm } = makeForm();

    loaded.handlers.setup(frm);

    assert.equal(loaded.autocompleteInstances.length, 2);
    assert.equal(controls.vehicle.control.df.fieldtype, undefined);
    assert.equal(controls.vehicle.inputArea.children.length, 1);
    assert.equal(
        controls.vehicle.control._nubefact_catalog_autocomplete.link_controls.visible,
        false
    );
    controls.vehicle.input.value = "camión";
    controls.vehicle.$input.trigger("input");

    assert.equal(searchRequest.method, "frappe.desk.search.search_link");
    assert.deepEqual(
        { ...searchRequest.args },
        {
            txt: "camión",
            doctype: "Nubefact Vehiculo",
            reference_doctype: "Nubefact Guia De Remision",
            page_length: 12,
        }
    );
    assert.deepEqual(loaded.autocompleteInstances[0].list, [
        { value: "ABC123", label: "Camión principal", description: "ABC123" },
    ]);
});

test("selecting a vehicle suggestion copies the plate to the unchanged GRE field", async () => {
    let request;
    const loaded = loadFormScript({
        call() {},
        getValue: async (doctype, name, fields) => {
            request = { doctype, fields: Array.from(fields), name };
            return { message: { placa_numero: "ABC123" } };
        },
    });
    const { controls, frm, getAssignedValues } = makeForm();
    loaded.handlers.setup(frm);
    let prevented = false;

    await autocompleteSelectHandler(controls.vehicle)({
        preventDefault() {
            prevented = true;
        },
        originalEvent: { text: { value: "ABC123" } },
    });

    assert.equal(prevented, true);
    assert.deepEqual(request, {
        doctype: "Nubefact Vehiculo",
        fields: ["placa_numero"],
        name: "ABC123",
    });
    assert.deepEqual(getAssignedValues(), { transportista_placa_numero: "ABC123" });
    assert.equal(loaded.autocompleteInstances[0].closed, true);
    assert.equal(
        controls.vehicle.control._nubefact_catalog_autocomplete.link_controls.visible,
        true
    );
});

test("the trailing clear control empties the field and opens its suggestions", async () => {
    let searchCount = 0;
    const loaded = loadFormScript({
        call(options) {
            searchCount += 1;
            options.callback({ message: [] });
        },
        getValue: async () => ({ message: null }),
    });
    const { controls, frm, getAssignedValues } = makeForm({
        transportista_placa_numero: "ABC123",
    });
    controls.vehicle.input.value = "ABC123";
    loaded.handlers.setup(frm);
    controls.vehicle.$input.trigger("focus");
    const clearButton = controls.vehicle.control._nubefact_catalog_autocomplete.clear_button;
    let prevented = false;
    let propagationStopped = false;

    await clearButton.handlers.click({
        preventDefault() {
            prevented = true;
        },
        stopPropagation() {
            propagationStopped = true;
        },
    });

    assert.equal(prevented, true);
    assert.equal(propagationStopped, true);
    assert.deepEqual(getAssignedValues(), { transportista_placa_numero: null });
    assert.equal(controls.vehicle.input.value, "");
    assert.equal(controls.vehicle.$input.focused, true);
    assert.ok(searchCount > 0);
});

test("the arrow resolves a driver key and routes to its catalog record", async () => {
    let existenceRequest;
    let route;
    const loaded = loadFormScript({
        call() {},
        getValue: async (doctype, name, fieldname) => {
            existenceRequest = { doctype, fieldname, name };
            return { message: { name } };
        },
        setRoute: (...parts) => {
            route = parts;
        },
    });
    const { controls, frm } = makeForm({ conductor_documento_tipo: "1" });
    controls.driver.input.value = "12345678";
    loaded.handlers.setup(frm);

    await controls.driver.control._nubefact_catalog_autocomplete.open_button.handlers.click({
        preventDefault() {},
        stopPropagation() {},
    });

    assert.deepEqual(existenceRequest, {
        doctype: "Nubefact Conductor",
        fieldname: "name",
        name: "1-12345678",
    });
    assert.deepEqual(route, ["Form", "Nubefact Conductor", "1-12345678"]);
});

test("the arrow reports when a free-form value has no catalog record", async () => {
    let message;
    let routed = false;
    const loaded = loadFormScript({
        call() {},
        getValue: async () => ({ message: null }),
        msgprint: (options) => {
            message = options;
        },
        setRoute: () => {
            routed = true;
        },
    });
    const { controls, frm } = makeForm();
    controls.vehicle.input.value = "FREE123";
    loaded.handlers.setup(frm);

    await controls.vehicle.control._nubefact_catalog_autocomplete.open_button.handlers.click({
        preventDefault() {},
        stopPropagation() {},
    });

    assert.equal(routed, false);
    assert.equal(message.title, "Registro no encontrado");
    assert.equal(
        message.message,
        "No existe un registro de Nubefact Vehiculo para la clave FREE123."
    );
    assert.equal(message.indicator, "orange");
});

test("selecting a driver suggestion copies every conductor field and an empty plate", async () => {
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
    const loaded = loadFormScript({
        call() {},
        getValue: async (_doctype, _name, fields) => {
            requestedFields = Array.from(fields);
            return { message: catalogValues };
        },
    });
    const { controls, frm, getAssignedValues } = makeForm();
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.driver)({
        preventDefault() {},
        originalEvent: { text: { value: "1-12345678" } },
    });

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
});

test("selecting a driver suggestion does not replace an existing GRE plate", async () => {
    const loaded = loadFormScript({
        call() {},
        getValue: async () => ({
            message: {
                documento_tipo: "1",
                documento_numero: "12345678",
                denominacion: null,
                nombre: "JUAN",
                apellidos: "PEREZ",
                numero_licencia: "Q12345678",
                vehiculo: "NEW123",
            },
        }),
    });
    const { controls, frm, getAssignedValues } = makeForm({
        transportista_placa_numero: "OLD123",
    });
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.driver)({
        preventDefault() {},
        originalEvent: { text: { value: "1-12345678" } },
    });

    assert.equal(getAssignedValues().transportista_placa_numero, undefined);
    assert.equal(frm.doc.transportista_placa_numero, "OLD123");
});
