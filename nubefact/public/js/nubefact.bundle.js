frappe.provide("nubefact");

class NubefactWatcher {
	constructor(frm, api_method, options = {}) {
		this.frm = frm;
		this.api_method = api_method;
		this.poll_interval_ms = options.poll_interval_ms || 5000;
		this.pending_status = options.pending_status || "Pending Response";
		this.initialized = false;
		this.in_flight = false;
		this.current_poll_promise = null;
		this.timeout_id = null;
	}

	on_refresh() {
		this.clear_poll();
		if (!this.is_pending_response()) {
			this.initialized = false;
		}
	}

	clear_poll() {
		if (this.timeout_id) {
			clearTimeout(this.timeout_id);
			this.timeout_id = null;
		}
	}

	is_pending_response() {
		return this.frm.doc.status === this.pending_status;
	}

	can_poll() {
		const current_form = cur_page?.page?.frm;
		if (!current_form) {
			return false;
		}

		if (current_form.doctype !== this.frm.doctype) {
			return false;
		}

        if (current_form.docname !== this.frm.docname) {
            return false;
        }

		return this.is_pending_response() && !this.frm.is_dirty();
	}

	async call_api(options = {}) {
		const freeze = options.freeze ?? true;
		const freeze_message = options.freeze_message ?? __("Refreshing SUNAT status...");

		await frappe.call({
			method: this.api_method,
			args: { name: this.frm.doc.name },
			freeze,
			freeze_message,
			...options,
		});
	}

	async run_poll_cycle() {
		if (!this.can_poll()) {
			return;
		}

		if (this.in_flight) {
			this.schedule_if_needed();
			return;
		}

		this.in_flight = true;
		this.current_poll_promise = (async () => {
			try {
				await this.call_api();
				await this.frm.reload_doc();
			} catch (error) {
				console.error("Failed to refresh pending status", error);
				this.schedule_if_needed();
			} finally {
				this.in_flight = false;
				this.current_poll_promise = null;
			}
		})();

		await this.current_poll_promise;
	}

	schedule_if_needed() {
		if (!this.can_poll()) {
			return;
		}

			const should_trigger_initial_delay = !this.initialized;
		this.initialized = true;

			if (should_trigger_initial_delay) {
				this.timeout_id = setTimeout(() => {
					void this.run_poll_cycle();
				}, 1500);
			return;
		}

		this.timeout_id = setTimeout(() => {
			void this.run_poll_cycle();
		}, this.poll_interval_ms);
	}

	async refresh_now_and_continue(options = {}) {
		this.clear_poll();
		await this.call_api(options);
		this.initialized = true;
		await this.frm.reload_doc();
		this.schedule_if_needed();
	}
}

nubefact.Watcher = NubefactWatcher;
nubefact.NubefactWatcher = NubefactWatcher;

nubefact.get_watcher = function(frm, api_method, options = {}) {
	if (!frm.__nubefact_watchers) {
		frm.__nubefact_watchers = {};
	}

	if (!frm.__nubefact_watchers[api_method]) {
		frm.__nubefact_watchers[api_method] = new nubefact.Watcher(frm, api_method, options);
	}

	return frm.__nubefact_watchers[api_method];
};

nubefact.hello = function() {
	console.log("Hello from Nubefact!");
};

console.log("Nubefact bundle loaded");
