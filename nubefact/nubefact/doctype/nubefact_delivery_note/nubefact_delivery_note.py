# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, cstr, now_datetime

from nubefact.nubefact.doctype.nubefact_branch.nubefact_branch import (
    get_last_used_branch_for_user,
)
from nubefact.nubefact.doctype.nubefact_branch.nubefact_branch import (
    get_origin_values as get_branch_origin_values,
)
from nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note_import import (
    create_delivery_note_from_import_file as _create_delivery_note_from_import_file,
)
from nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note_import import (
    create_delivery_note_from_import_json_text as _create_delivery_note_from_import_json_text,
)
from nubefact.nubefact.doctype.nubefact_delivery_note.nubefact_delivery_note_schema import (
    ITEM_REQUIRED_FIELDS,
    RELATED_DOCUMENT_REQUIRED_FIELDS,
    SECONDARY_DRIVER_REQUIRED_FIELDS,
    SECONDARY_VEHICLE_REQUIRED_FIELDS,
    SUBMIT_REQUIRED_FIELDS,
    TYPE_8_RECIPIENT_REQUIRED_FIELDS,
)
from nubefact.utils import (
    make_request,
    require_child_fields,
    require_fields,
    to_nubefact_date,
)

_CLEARED_RESPONSE_VALUES: dict[str, Any] = {
    "accepted_by_sunat": 0,
    "last_sunat_check": None,
    "sunat_response_code": "",
    "sunat_response_message": "",
    "sunat_note": "",
    "sunat_soap_error": "",
    "error_message": "",
    "link_url": "",
    "pdf_url": "",
    "xml_url": "",
    "cdr_url": "",
    "qr_url": "",
}


class NubefactDeliveryNote(Document):
    def autoname(self):
        timestamp = now_datetime()
        self.name = append_number_if_name_exists(
            "Nubefact Delivery Note", timestamp.strftime("%Y%m%d-%H%M%S-%f")
        )

    def autotitle(self):
        series = cstr(self.series or "").strip()
        number = cstr(self.number or "").strip()
        self.title = f"{series}-{number}" if (series or number) else ""

    def validate(self):
        if not self.status:
            self.status = "Draft"

        self._set_inferred_values()

        if not cint(getattr(self, "skip_required_fields_validation", 0)):
            self._validate_submit_payload()

    def _set_inferred_values(self):
        if not cstr(self.branch or "").strip():
            last_branch = get_last_used_branch_for_user(
                doctype=self.doctype,
                user=frappe.session.user,
                exclude_name=self.name,
            )

            if last_branch:
                self.branch = last_branch

        branch_origin_values = get_branch_origin_values(self.branch)
        inferred_origin_fields = (
            ("origin_ubigeo", branch_origin_values.get("origin_ubigeo")),
            ("origin_address", branch_origin_values.get("origin_address")),
            ("origin_sunat_code", branch_origin_values.get("origin_sunat_code")),
        )

        for fieldname, inferred_value in inferred_origin_fields:
            if not cstr(self.get(fieldname) or "").strip() and inferred_value:
                self.set(fieldname, inferred_value)

        self.autotitle()

    def _build_generate_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operacion": "generar_guia",
            "tipo_de_comprobante": cint(self.document_type),
            "serie": self.series,
            "cliente_tipo_de_documento": cstr(self.client_document_type),
            "cliente_numero_de_documento": self.client_document_number,
            "cliente_denominacion": self.client_name,
            "cliente_direccion": self.client_address,
            "fecha_de_emision": to_nubefact_date(self.issue_date),
            "fecha_de_inicio_de_traslado": to_nubefact_date(self.transfer_start_date),
            "motivo_de_traslado": cstr(self.transfer_reason),
            "peso_bruto_total": cstr(self.gross_total_weight),
            "peso_bruto_unidad_de_medida": self.weight_unit,
            "numero_de_bultos": cstr(self.number_of_packages),
            "tipo_de_transporte": cstr(self.transport_type),
            "punto_de_partida_ubigeo": self.origin_ubigeo,
            "punto_de_partida_direccion": self.origin_address,
            "punto_de_llegada_ubigeo": self.destination_ubigeo,
            "punto_de_llegada_direccion": self.destination_address,
            "enviar_automaticamente_al_cliente": (
                "true" if cint(self.auto_send_to_client) else "false"
            ),
            "formato_de_pdf": cstr(self.pdf_format or ""),
            "items": [
                {
                    "unidad_de_medida": row.unit_of_measure,
                    "codigo": row.item_code,
                    "descripcion": row.description,
                    "cantidad": cstr(row.quantity),
                }
                for row in self.items
            ],
        }

        _set_if_value(payload, "numero", self.number)

        _set_if_value(payload, "cliente_email", self.client_email)
        _set_if_value(payload, "cliente_email_1", self.client_email_1)
        _set_if_value(payload, "cliente_email_2", self.client_email_2)
        _set_if_value(payload, "observaciones", self.observations)
        _set_if_value(
            payload,
            "punto_de_partida_codigo_establecimiento_sunat",
            self.origin_sunat_code,
        )
        _set_if_value(
            payload,
            "punto_de_llegada_codigo_establecimiento_sunat",
            self.destination_sunat_code,
        )

        _set_if_value(
            payload, "transportista_documento_tipo", self.carrier_document_type
        )
        _set_if_value(
            payload,
            "transportista_documento_numero",
            self.carrier_document_number,
        )
        _set_if_value(payload, "transportista_denominacion", self.carrier_name)
        _set_if_value(payload, "transportista_placa_numero", self.vehicle_license_plate)
        _set_if_value(payload, "conductor_documento_tipo", self.driver_document_type)
        _set_if_value(
            payload, "conductor_documento_numero", self.driver_document_number
        )
        _set_if_value(payload, "conductor_nombre", self.driver_first_name)
        _set_if_value(payload, "conductor_apellidos", self.driver_last_name)
        _set_if_value(payload, "conductor_numero_licencia", self.driver_license_number)

        if cstr(self.document_type) == "8":
            payload["destinatario_documento_tipo"] = cstr(self.recipient_document_type)
            payload["destinatario_documento_numero"] = self.recipient_document_number
            payload["destinatario_denominacion"] = self.recipient_name

        if self.related_documents:
            payload["documento_relacionado"] = [
                {
                    "tipo": cstr(row.document_type),
                    "serie": row.series,
                    "numero": cstr(row.number),
                }
                for row in self.related_documents
            ]

        if self.secondary_vehicles:
            payload["vehiculos_secundarios"] = []
            for row in self.secondary_vehicles:
                vehicle = {"placa_numero": row.license_plate}
                _set_if_value(vehicle, "tuc", row.tuc)
                payload["vehiculos_secundarios"].append(vehicle)

        if self.secondary_drivers:
            payload["conductores_secundarios"] = [
                {
                    "documento_tipo": cstr(row.document_type),
                    "documento_numero": row.document_number,
                    "nombre": row.first_name,
                    "apellidos": row.last_name,
                    "numero_licencia": row.license_number,
                }
                for row in self.secondary_drivers
            ]

        return payload

    def _validate_submit_payload(self):
        require_fields(
            self,
            SUBMIT_REQUIRED_FIELDS,
            "Required fields are missing for Delivery Note submission.",
        )

        if not self.items:
            frappe.throw("At least one item is required for Delivery Note submission.")

        for index, row in enumerate(self.items, start=1):
            require_child_fields(
                row,
                ITEM_REQUIRED_FIELDS,
                f"Items row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.related_documents or [], start=1):
            require_child_fields(
                row,
                RELATED_DOCUMENT_REQUIRED_FIELDS,
                f"Related Documents row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.secondary_vehicles or [], start=1):
            require_child_fields(
                row,
                SECONDARY_VEHICLE_REQUIRED_FIELDS,
                f"Secondary Vehicles row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.secondary_drivers or [], start=1):
            require_child_fields(
                row,
                SECONDARY_DRIVER_REQUIRED_FIELDS,
                f"Secondary Drivers row #{index} has missing required fields.",
            )

        if cstr(self.document_type) == "8":
            require_fields(
                self,
                TYPE_8_RECIPIENT_REQUIRED_FIELDS,
                "Recipient fields are required for Delivery Note type 8.",
            )

    def _apply_generate_response(self, response: Any):
        self.update(self._extract_response_values(response))

    def _build_consult_payload(self) -> dict[str, Any]:
        return {
            "operacion": "consultar_guia",
            "tipo_de_comprobante": cint(self.document_type),
            "serie": self.series,
            "numero": cstr(self.number),
        }

    def _extract_response_values(self, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        accepted_by_sunat = 1 if response.get("aceptada_por_sunat") else 0
        number = response.get("numero") or self.number
        series = cstr(self.series or "").strip()
        number_text = cstr(number or "").strip()
        title = f"{series}-{number_text}" if (series or number_text) else ""

        return {
            "number": number,
            "title": title,
            "status": "Accepted" if accepted_by_sunat else "Pending Response",
            "accepted_by_sunat": accepted_by_sunat,
            "last_sunat_check": now_datetime(),
            "sunat_response_code": cstr(response.get("sunat_responsecode") or ""),
            "sunat_response_message": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "error_message": cstr(response.get("sunat_soap_error") or ""),
            "link_url": cstr(response.get("enlace") or ""),
            "pdf_url": cstr(response.get("enlace_del_pdf") or ""),
            "xml_url": cstr(response.get("enlace_del_xml") or ""),
            "cdr_url": cstr(response.get("enlace_del_cdr") or ""),
            "qr_url": cstr(response.get("cadena_para_codigo_qr") or ""),
        }


@frappe.whitelist()
def send_to_nubefact(name: str):

    doc = frappe.get_doc("Nubefact Delivery Note", name)
    doc.check_permission("write")

    if doc.status not in {"Draft", "Error"}:
        frappe.throw("Only Draft or Error delivery notes can be sent to Nubefact.")

    try:
        doc.run_method("validate")

        payload = doc._build_generate_payload()

        response = make_request(
            payload=payload,
            branch=doc.branch,
            operation="generar_guia",
            reference_delivery_note=doc.name,
        )
        values = doc._extract_response_values(response)
    except Exception as exc:
        frappe.db.rollback()
        error_message = cstr(exc)
        values = {
            "status": "Error",
            "accepted_by_sunat": 0,
            "last_sunat_check": now_datetime(),
            "error_message": error_message,
        }

    if values:
        _save_response_status(doc, values)

    if values and values.get("status") == "Error":
        frappe.db.commit()

    return values


@frappe.whitelist()
def refresh_sunat_status(name: str):
    doc = frappe.get_doc("Nubefact Delivery Note", name)
    return _refresh_sunat_status_doc(doc, enforce_permission=True)


@frappe.whitelist()
def create_delivery_note_from_import_file(file_name: str) -> str:
    return _create_delivery_note_from_import_file(file_name)


@frappe.whitelist()
def create_delivery_note_from_import_json_text(json_payload: str) -> str:
    return _create_delivery_note_from_import_json_text(json_payload)


def poll_pending_delivery_notes():
    pending_names = frappe.get_all(
        "Nubefact Delivery Note",
        filters={"status": "Pending Response", "accepted_by_sunat": 0},
        pluck="name",
        limit=20,
        order_by="modified asc",
    )

    for name in pending_names:
        try:
            doc = frappe.get_doc("Nubefact Delivery Note", name)
            _refresh_sunat_status_doc(doc, enforce_permission=False)
        except Exception:
            frappe.log_error(
                title=f"Nubefact Delivery Note SUNAT refresh failed: {name}",
                message=frappe.get_traceback(),
            )


def _set_if_value(payload: dict[str, Any], key: str, value: Any):
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
        return

    payload[key] = value


def _refresh_sunat_status_doc(
    doc: NubefactDeliveryNote, *, enforce_permission: bool
) -> dict[str, Any]:
    if enforce_permission:
        doc.check_permission("read")

    if not doc.number:
        frappe.throw("Cannot refresh SUNAT status because document number is missing.")

    response = make_request(
        payload=doc._build_consult_payload(),
        branch=doc.branch,
        operation="consultar_guia",
        reference_delivery_note=doc.name,
    )
    values = doc._extract_response_values(response)

    if values:
        _save_response_status(doc, values)

    return values


def _save_response_status(
    doc: NubefactDeliveryNote, values: dict[str, Any]
) -> dict[str, Any]:
    if not values:
        return {}

    cleared_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES)
    cleared_values.update(values)

    doc.update(cleared_values)
    doc.autotitle()

    doc.db_update()
    doc.notify_update()

    return cleared_values
