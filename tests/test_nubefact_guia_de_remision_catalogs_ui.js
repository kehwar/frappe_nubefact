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
        remove() {
            this.removed = true;
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
    const displayArea = makeJqueryElement();
    return {
        ...input,
        displayArea,
        inputArea,
        control: {
            $input: input.$input,
            $wrapper: {
                find(selector) {
                    if (selector === ".control-input") return inputArea;
                    assert.equal(selector, ".control-value");
                    return displayArea;
                },
            },
            can_write: () => true,
            df: {},
            input: input.input,
        },
    };
}

function loadFormScript({
    call,
    getList = async () => [],
    getValue,
    msgprint = () => {},
    setRoute = () => {},
}) {
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
            db: { get_list: getList, get_value: getValue },
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
    const originEstablishment = makeControl();
    const destinationEstablishment = makeControl();
    const controlsByFieldname = {
        conductor_documento_numero: driver,
        punto_de_llegada_codigo_establecimiento_sunat: destinationEstablishment,
        punto_de_partida_codigo_establecimiento_sunat: originEstablishment,
        transportista_placa_numero: vehicle,
    };
    const frm = {
        doctype: "Nubefact Guia De Remision",
        doc,
        docname: initialValues.name || "NEW-GRE-1",
        fields_dict: Object.fromEntries(
            Object.entries(controlsByFieldname).map(([fieldname, entry]) => [
                fieldname,
                entry.control,
            ])
        ),
        set_query() {},
        async set_value(fieldname, value) {
            const values =
                typeof fieldname === "string" ? { [fieldname]: value } : { ...fieldname };
            assignedValues = values;
            Object.assign(doc, values);
            for (const [targetFieldname, targetValue] of Object.entries(values)) {
                if (controlsByFieldname[targetFieldname]) {
                    controlsByFieldname[targetFieldname].input.value = targetValue || "";
                }
            }
        },
    };
    return {
        controls: { destinationEstablishment, driver, originEstablishment, vehicle },
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

    assert.equal(loaded.autocompleteInstances.length, 4);
    assert.equal(controls.vehicle.control.df.fieldtype, undefined);
    assert.equal(controls.vehicle.inputArea.children.length, 1);
    assert.equal(controls.vehicle.displayArea.children.length, 1);
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

test("establishment autocomplete searches company locals with SUNAT codes", () => {
    let searchRequest;
    const loaded = loadFormScript({
        call(options) {
            searchRequest = options;
            options.callback({
                message: [
                    {
                        value: "Almacén Lima-ACME",
                        label: "Almacén Lima",
                        description: "0002, LIMA",
                    },
                ],
            });
        },
        getValue: async () => ({ message: null }),
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    loaded.handlers.setup(frm);

    controls.originEstablishment.input.value = "0002";
    controls.originEstablishment.$input.trigger("input");

    assert.deepEqual(JSON.parse(JSON.stringify(searchRequest.args)), {
        txt: "0002",
        doctype: "Nubefact Local",
        reference_doctype: "Nubefact Guia De Remision",
        page_length: 12,
        filters: {
            company: "ACME",
            codigo_sunat: ["is", "set"],
        },
    });
});

test("selecting a destination establishment copies its code and location", async () => {
    let request;
    const loaded = loadFormScript({
        call() {},
        getValue: async (doctype, name, fields) => {
            request = { doctype, fields: Array.from(fields), name };
            return {
                message: {
                    codigo_sunat: "0002",
                    direccion: "AV. INDUSTRIAL 123",
                    ubigeo: "150101",
                },
            };
        },
    });
    const { controls, frm, getAssignedValues } = makeForm({ company: "ACME" });
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.destinationEstablishment)({
        preventDefault() {},
        originalEvent: { text: { value: "Almacén Lima-ACME" } },
    });

    assert.deepEqual(JSON.parse(JSON.stringify(request)), {
        doctype: "Nubefact Local",
        fields: ["codigo_sunat", "ubigeo", "direccion"],
        name: {
            name: "Almacén Lima-ACME",
            company: "ACME",
        },
    });
    assert.deepEqual(getAssignedValues(), {
        punto_de_llegada_codigo_establecimiento_sunat: "0002",
        punto_de_llegada_ubigeo: "150101",
        punto_de_llegada_direccion: "AV. INDUSTRIAL 123",
    });
});

test("clearing an establishment code leaves its manually editable location intact", async () => {
    const loaded = loadFormScript({
        call(options) {
            options.callback({ message: [] });
        },
        getValue: async () => ({ message: null }),
    });
    const { controls, frm, getAssignedValues } = makeForm({
        company: "ACME",
        punto_de_partida_codigo_establecimiento_sunat: "0001",
        punto_de_partida_direccion: "AV. ORIGEN 123",
        punto_de_partida_ubigeo: "150101",
    });
    controls.originEstablishment.input.value = "0001";
    loaded.handlers.setup(frm);

    await controls.originEstablishment.control._nubefact_catalog_autocomplete.clear_button.handlers.click(
        {
            preventDefault() {},
            stopPropagation() {},
        }
    );

    assert.deepEqual(getAssignedValues(), {
        punto_de_partida_codigo_establecimiento_sunat: null,
    });
    assert.equal(frm.doc.punto_de_partida_direccion, "AV. ORIGEN 123");
    assert.equal(frm.doc.punto_de_partida_ubigeo, "150101");
});

test("the establishment shortcut opens the unique matching company local", async () => {
    let listRequest;
    let route;
    const loaded = loadFormScript({
        call() {},
        getList: async (doctype, options) => {
            listRequest = { doctype, options };
            return [{ name: "Almacén Lima-ACME" }];
        },
        getValue: async () => ({ message: null }),
        setRoute: (...parts) => {
            route = parts;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    controls.originEstablishment.input.value = "0002";
    loaded.handlers.setup(frm);

    await controls.originEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
        {
            preventDefault() {},
            stopPropagation() {},
        }
    );

    assert.deepEqual(JSON.parse(JSON.stringify(listRequest)), {
        doctype: "Nubefact Local",
        options: {
            fields: ["name"],
            filters: { codigo_sunat: "0002", company: "ACME" },
            limit: 2,
        },
    });
    assert.deepEqual(route, ["Form", "Nubefact Local", "Almacén Lima-ACME"]);
});

test("the establishment shortcut refuses to choose between duplicate codes", async () => {
    let message;
    let routed = false;
    const loaded = loadFormScript({
        call() {},
        getList: async () => [{ name: "Local A-ACME" }, { name: "Local B-ACME" }],
        getValue: async () => ({ message: null }),
        msgprint: (options) => {
            message = options;
        },
        setRoute: () => {
            routed = true;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    controls.destinationEstablishment.input.value = "0000";
    loaded.handlers.setup(frm);

    await controls.destinationEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
        {
            preventDefault() {},
            stopPropagation() {},
        }
    );

    assert.equal(routed, false);
    assert.equal(message.title, "Más de un registro encontrado");
    assert.equal(
        message.message,
        "Más de un registro de Nubefact Local coincide con la clave 0000. Seleccione el registro desde las sugerencias."
    );
    assert.equal(message.indicator, "orange");
});

test("an establishment search response is ignored after the company changes", () => {
    let respond;
    const loaded = loadFormScript({
        call(options) {
            respond = options.callback;
        },
        getValue: async () => ({ message: null }),
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    loaded.handlers.setup(frm);

    controls.originEstablishment.input.value = "0002";
    controls.originEstablishment.$input.trigger("input");
    frm.doc.company = "OTHER";
    respond({
        message: [{ value: "Almacén Lima-ACME", label: "Almacén Lima" }],
    });

    assert.equal(loaded.autocompleteInstances[2].list.length, 0);
});

test("catalog shortcuts remain available while clear controls are read-only", () => {
    const loaded = loadFormScript({
        call() {},
        getValue: async () => ({ message: null }),
    });
    const { controls, frm } = makeForm({ transportista_placa_numero: "ABC123" });
    controls.vehicle.control.can_write = () => false;
    controls.vehicle.input.value = "ABC123";
    loaded.handlers.setup(frm);

    controls.vehicle.inputArea.handlers["mouseenter.nubefactCatalogAutocomplete"]();
    const state = controls.vehicle.control._nubefact_catalog_autocomplete;

    assert.equal(state.link_controls.visible, false);
    assert.equal(state.clear_button.visible, false);
    assert.equal(state.open_button.visible, false);
    assert.equal(state.read_only_open_button.visible, true);
});

test("a selected duplicate establishment retains its exact open shortcut", async () => {
    let listCalls = 0;
    let route;
    const loaded = loadFormScript({
        call() {},
        getList: async () => {
            listCalls += 1;
            return [{ name: "Local A-ACME" }, { name: "Local B-ACME" }];
        },
        getValue: async () => ({
            message: {
                codigo_sunat: "0000",
                direccion: "AV. A",
                ubigeo: "150101",
            },
        }),
        setRoute: (...parts) => {
            route = parts;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.originEstablishment)({
        preventDefault() {},
        originalEvent: { text: { value: "Local A-ACME" } },
    });
    await controls.originEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
        {
            preventDefault() {},
            stopPropagation() {},
        }
    );

    assert.equal(listCalls, 0);
    assert.deepEqual(route, ["Form", "Nubefact Local", "Local A-ACME"]);
});

test("an in-flight establishment selection is ignored after the company changes", async () => {
    let resolveGetValue;
    const loaded = loadFormScript({
        call() {},
        getValue: () =>
            new Promise((resolve) => {
                resolveGetValue = resolve;
            }),
    });
    const { controls, frm, getAssignedValues } = makeForm({ company: "ACME" });
    loaded.handlers.setup(frm);

    const selection = autocompleteSelectHandler(controls.originEstablishment)({
        preventDefault() {},
        originalEvent: { text: { value: "Local A-ACME" } },
    });
    frm.doc.company = "OTHER";
    resolveGetValue({
        message: {
            codigo_sunat: "0000",
            direccion: "AV. A",
            ubigeo: "150101",
        },
    });
    await selection;

    assert.deepEqual(getAssignedValues(), {});
    assert.equal(frm.doc.punto_de_partida_codigo_establecimiento_sunat, undefined);
});

test("read-only catalog shortcuts initialize when Frappe has not created an input", () => {
    const loaded = loadFormScript({
        call() {},
        getValue: async () => ({ message: null }),
    });
    const { controls, frm } = makeForm({ transportista_placa_numero: "ABC123" });
    controls.vehicle.control.can_write = () => false;
    controls.vehicle.control.$input = null;
    controls.vehicle.control.input = null;

    loaded.handlers.setup(frm);

    const state = controls.vehicle.control._nubefact_catalog_autocomplete;
    assert.equal(state.awesomplete, null);
    assert.equal(controls.vehicle.displayArea.children.length, 1);
    assert.equal(state.read_only_open_button.visible, true);
});

test("changing driver identity invalidates the selected-record shortcut", async () => {
    let getValueCalls = 0;
    let route;
    const loaded = loadFormScript({
        call() {},
        getValue: async (_doctype, name) => {
            getValueCalls += 1;
            if (getValueCalls === 1) {
                return {
                    message: {
                        documento_tipo: "1",
                        documento_numero: "12345678",
                        denominacion: null,
                        nombre: "JUAN",
                        apellidos: "PEREZ",
                        numero_licencia: "Q12345678",
                        vehiculo: null,
                    },
                };
            }
            return { message: { name } };
        },
        setRoute: (...parts) => {
            route = parts;
        },
    });
    const { controls, frm } = makeForm({ conductor_documento_tipo: "1" });
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.driver)({
        preventDefault() {},
        originalEvent: { text: { value: "1-12345678" } },
    });
    frm.doc.conductor_documento_tipo = "6";
    await controls.driver.control._nubefact_catalog_autocomplete.open_button.handlers.click({
        preventDefault() {},
        stopPropagation() {},
    });

    assert.equal(getValueCalls, 2);
    assert.deepEqual(route, ["Form", "Nubefact Conductor", "6-12345678"]);
});

test("an in-flight establishment shortcut is ignored after the company changes", async () => {
    let resolveGetList;
    let routed = false;
    const loaded = loadFormScript({
        call() {},
        getList: () =>
            new Promise((resolve) => {
                resolveGetList = resolve;
            }),
        getValue: async () => ({ message: null }),
        setRoute: () => {
            routed = true;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    controls.originEstablishment.input.value = "0002";
    loaded.handlers.setup(frm);

    const opening =
        controls.originEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
            {
                preventDefault() {},
                stopPropagation() {},
            }
        );
    frm.doc.company = "OTHER";
    resolveGetList([{ name: "Almacén Lima-ACME" }]);
    await opening;

    assert.equal(routed, false);
});

test("an in-flight establishment selection is ignored after navigating to another GRE", async () => {
    let resolveGetValue;
    const loaded = loadFormScript({
        call() {},
        getValue: () =>
            new Promise((resolve) => {
                resolveGetValue = resolve;
            }),
    });
    const { controls, frm, getAssignedValues } = makeForm({
        company: "ACME",
        name: "GRE-1",
    });
    loaded.handlers.setup(frm);

    const selection = autocompleteSelectHandler(controls.destinationEstablishment)({
        preventDefault() {},
        originalEvent: { text: { value: "Local A-ACME" } },
    });
    frm.docname = "GRE-2";
    frm.doc.name = "GRE-2";
    resolveGetValue({
        message: {
            codigo_sunat: "0000",
            direccion: "AV. A",
            ubigeo: "150101",
        },
    });
    await selection;

    assert.deepEqual(getAssignedValues(), {});
});

test("an in-flight catalog shortcut is ignored after its key changes", async () => {
    let resolveGetList;
    let routed = false;
    const loaded = loadFormScript({
        call() {},
        getList: () =>
            new Promise((resolve) => {
                resolveGetList = resolve;
            }),
        getValue: async () => ({ message: null }),
        setRoute: () => {
            routed = true;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME" });
    controls.originEstablishment.input.value = "0002";
    loaded.handlers.setup(frm);

    const opening =
        controls.originEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
            {
                preventDefault() {},
                stopPropagation() {},
            }
        );
    controls.originEstablishment.input.value = "0003";
    controls.originEstablishment.$input.trigger("input");
    resolveGetList([{ name: "Almacén Lima-ACME" }]);
    await opening;

    assert.equal(routed, false);
});

test("a duplicate establishment shortcut does not leak into another GRE", async () => {
    let listCalls = 0;
    let message;
    let routed = false;
    const loaded = loadFormScript({
        call() {},
        getList: async () => {
            listCalls += 1;
            return [{ name: "Local A-ACME" }, { name: "Local B-ACME" }];
        },
        getValue: async () => ({
            message: {
                codigo_sunat: "0000",
                direccion: "AV. A",
                ubigeo: "150101",
            },
        }),
        msgprint: (options) => {
            message = options;
        },
        setRoute: () => {
            routed = true;
        },
    });
    const { controls, frm } = makeForm({ company: "ACME", name: "GRE-1" });
    loaded.handlers.setup(frm);

    await autocompleteSelectHandler(controls.originEstablishment)({
        preventDefault() {},
        originalEvent: { text: { value: "Local A-ACME" } },
    });
    frm.docname = "GRE-2";
    frm.doc.name = "GRE-2";
    await controls.originEstablishment.control._nubefact_catalog_autocomplete.open_button.handlers.click(
        {
            preventDefault() {},
            stopPropagation() {},
        }
    );

    assert.equal(listCalls, 1);
    assert.equal(routed, false);
    assert.equal(message.title, "Más de un registro encontrado");
});
