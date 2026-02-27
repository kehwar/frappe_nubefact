# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, cstr, getdate, now_datetime

from nubefact.utils.nubefact import make_request


class NubefactDeliveryNote(Document):
    def autoname(self):
        timestamp = now_datetime()
        self.name = append_number_if_name_exists(
            "Nubefact Delivery Note", timestamp.strftime("%Y%m%d-%H%M%S-%f")
        )

    def validate(self):
        self.title = _build_delivery_note_title(
            document_type=self.document_type,
            series=self.series,
            number=self.number,
        )

    def before_submit(self):
        payload = self._build_generate_payload()
        response = make_request(
            payload=payload,
            branch=self.branch,
            operation="generar_guia",
            reference_delivery_note=self.name,
        )
        self._apply_generate_response(response)

    def _build_generate_payload(self) -> dict[str, Any]:
        self._validate_submit_payload()

        payload: dict[str, Any] = {
            "operacion": "generar_guia",
            "tipo_de_comprobante": cint(self.document_type),
            "serie": self.series,
            "numero": cstr(self.number),
            "cliente_tipo_de_documento": cstr(self.client_document_type),
            "cliente_numero_de_documento": self.client_document_number,
            "cliente_denominacion": self.client_name,
            "cliente_direccion": self.client_address,
            "fecha_de_emision": _to_nubefact_date(self.issue_date),
            "fecha_de_inicio_de_traslado": _to_nubefact_date(self.transfer_start_date),
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
        _require_fields(
            self,
            [
                "document_type",
                "series",
                "number",
                "issue_date",
                "transfer_start_date",
                "client_document_type",
                "client_document_number",
                "client_name",
                "client_address",
                "transfer_reason",
                "transport_type",
                "gross_total_weight",
                "weight_unit",
                "number_of_packages",
                "origin_ubigeo",
                "origin_address",
                "destination_ubigeo",
                "destination_address",
            ],
            "Required fields are missing for Delivery Note submission.",
        )

        if not self.items:
            frappe.throw("At least one item is required for Delivery Note submission.")

        for index, row in enumerate(self.items, start=1):
            _require_child_fields(
                row,
                ["unit_of_measure", "item_code", "description", "quantity"],
                f"Items row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.related_documents or [], start=1):
            _require_child_fields(
                row,
                ["document_type", "series", "number"],
                f"Related Documents row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.secondary_vehicles or [], start=1):
            _require_child_fields(
                row,
                ["license_plate"],
                f"Secondary Vehicles row #{index} has missing required fields.",
            )

        for index, row in enumerate(self.secondary_drivers or [], start=1):
            _require_child_fields(
                row,
                [
                    "document_type",
                    "document_number",
                    "first_name",
                    "last_name",
                    "license_number",
                ],
                f"Secondary Drivers row #{index} has missing required fields.",
            )

        if cstr(self.document_type) == "8":
            _require_fields(
                self,
                [
                    "recipient_document_type",
                    "recipient_document_number",
                    "recipient_name",
                ],
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

        return {
            "accepted_by_sunat": 1 if response.get("aceptada_por_sunat") else 0,
            "last_sunat_check": now_datetime(),
            "sunat_response_code": cstr(response.get("sunat_responsecode") or ""),
            "sunat_response_message": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "link_url": cstr(response.get("enlace") or ""),
            "pdf_url": cstr(response.get("enlace_del_pdf") or ""),
            "xml_url": cstr(response.get("enlace_del_xml") or ""),
            "cdr_url": cstr(response.get("enlace_del_cdr") or ""),
            "qr_url": cstr(response.get("cadena_para_codigo_qr") or ""),
        }


@frappe.whitelist()
def refresh_sunat_status(name: str):
    doc = frappe.get_doc("Nubefact Delivery Note", name)
    return _refresh_sunat_status_doc(doc, enforce_permission=True)


def poll_pending_delivery_notes():
    pending_names = frappe.get_all(
        "Nubefact Delivery Note",
        filters={"docstatus": 1, "accepted_by_sunat": 0},
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

    payload[key] = value


def _refresh_sunat_status_doc(
    doc: NubefactDeliveryNote, *, enforce_permission: bool
) -> dict[str, Any]:
    if enforce_permission:
        doc.check_permission("read")

    if doc.docstatus != 1:
        frappe.throw("You can refresh SUNAT status only for submitted Delivery Notes.")

    response = make_request(
        payload=doc._build_consult_payload(),
        branch=doc.branch,
        operation="consultar_guia",
        reference_delivery_note=doc.name,
    )
    values = doc._extract_response_values(response)

    if values:
        frappe.db.set_value(doc.doctype, doc.name, values, update_modified=True)

    return values


def _to_nubefact_date(value: str) -> str:
    return getdate(value).strftime("%d-%m-%Y")


def _require_fields(doc: Document, fields: list[str], message: str):
    missing = [
        fieldname
        for fieldname in fields
        if not doc.get(fieldname)
        or (isinstance(doc.get(fieldname), str) and not doc.get(fieldname).strip())
    ]

    if missing:
        frappe.throw(message)


def _require_child_fields(row: Document, fields: list[str], message: str):
    missing = [
        fieldname
        for fieldname in fields
        if not row.get(fieldname)
        or (isinstance(row.get(fieldname), str) and not row.get(fieldname).strip())
    ]

    if missing:
        frappe.throw(message)


def _build_delivery_note_title(document_type: Any, series: Any, number: Any) -> str:
    prefix = (
        "R" if cstr(document_type) == "7" else "T" if cstr(document_type) == "8" else ""
    )

    if not prefix:
        return ""

    return f"{prefix}-{cstr(series or '').strip()}-{cstr(number or '').strip()}"
