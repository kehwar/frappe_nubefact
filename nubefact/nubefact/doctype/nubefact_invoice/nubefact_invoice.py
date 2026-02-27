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
from nubefact.nubefact.doctype.nubefact_invoice.nubefact_invoice_schema import (
    CREDIT_NOTE_REQUIRED_FIELDS,
    DEBIT_NOTE_REQUIRED_FIELDS,
    DELIVERY_REFERENCE_REQUIRED_FIELDS,
    ITEM_REQUIRED_FIELDS,
    NOTE_REFERENCE_REQUIRED_FIELDS,
    PAYMENT_INSTALLMENT_REQUIRED_FIELDS,
    REQUIRED_FIELDS,
)
from nubefact.utils import (
    apply_raw_payload_overrides,
    make_request,
    omit_empty_values,
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


class NubefactInvoice(Document):

    def autoname(self):
        timestamp = now_datetime()
        self.name = append_number_if_name_exists(
            "Nubefact Invoice", timestamp.strftime("%Y%m%d-%H%M%S-%f")
        )

    def validate(self):
        if not self.status:
            self.status = "Draft"

        self._set_inferred_values()

        if not cint(getattr(self, "skip_required_fields_validation", 0)):
            self._validate_required_fields()

    def _set_inferred_values(self):
        if not cstr(self.branch or "").strip():
            last_branch = get_last_used_branch_for_user(
                doctype=self.doctype,
                user=frappe.session.user,
                exclude_name=self.name,
            )

            if last_branch:
                self.branch = last_branch

        self.title = self._compose_title()

    def _compose_title(self, number: Any | None = None) -> str:
        series = cstr(self.series or "").strip()
        number_text = cstr((self.number if number is None else number) or "").strip()
        return f"{series}-{number_text}" if (series or number_text) else ""

    def _build_generate_payload(self) -> dict[str, Any]:
        items_payload = [
            apply_raw_payload_overrides(
                omit_empty_values(
                    {
                        "unidad_de_medida": row.uom,
                        "codigo": row.item_code,
                        "codigo_producto_sunat": row.sunat_product_code,
                        "descripcion": row.description,
                        "cantidad": cstr(row.quantity),
                        "valor_unitario": cstr(row.unit_price),
                        "precio_unitario": cstr(row.unit_price_with_tax),
                        "descuento": cstr(row.discount),
                        "subtotal": cstr(row.line_total),
                        "tipo_de_igv": cstr(row.igv_type),
                        "igv": cstr(row.igv),
                        "total": cstr(row.line_total_with_tax),
                        "anticipo_regularizacion": bool(
                            cint(row.downpayment_regularization)
                        ),
                        "anticipo_documento_serie": row.downpayment_document_series,
                        "anticipo_documento_numero": row.downpayment_document_number,
                    }
                ),
                row.raw,
                f"items row #{row.idx}",
            )
            for row in self.items
        ]

        payload: dict[str, Any] = {
            "operacion": "generar_comprobante",
            "tipo_de_comprobante": cint(self.document_type),
            "serie": self.series,
            "cliente_tipo_de_documento": cstr(self.client_document_type),
            "cliente_numero_de_documento": self.client_document_number,
            "cliente_denominacion": self.client_name,
            "cliente_direccion": self.client_address,
            "fecha_de_emision": to_nubefact_date(self.issue_date),
            "moneda": cstr(self.currency),
            "porcentaje_de_igv": cstr(self.igv_percentage),
            "total_igv": cstr(self.total_igv),
            "total": cstr(self.total),
            "enviar_automaticamente_a_la_sunat": bool(cint(self.auto_send_to_sunat)),
            "enviar_automaticamente_al_cliente": bool(cint(self.auto_send_to_client)),
            "formato_de_pdf": cstr(self.pdf_format or ""),
            "items": items_payload,
        }

        payload.update(
            omit_empty_values(
                {
                    "numero": self.number,
                    "sunat_transaction": cstr(self.sunat_transaction),
                    "fecha_de_vencimiento": (
                        to_nubefact_date(self.due_date) if self.due_date else None
                    ),
                    "cliente_email": self.client_email,
                    "cliente_email_1": self.client_email_1,
                    "cliente_email_2": self.client_email_2,
                    "total_gravada": cstr(self.total_taxable),
                    "total_inafecta": cstr(self.total_unaffected),
                    "total_exonerada": cstr(self.total_exempt),
                    "total_descuento": cstr(self.total_discount),
                    "total_anticipo": cstr(self.total_advance),
                    "total_gratuita": cstr(self.total_free),
                    "total_otros_cargos": cstr(self.total_other_charges),
                    "descuento_global": cstr(self.global_discount),
                    "tipo_de_cambio": cstr(self.exchange_rate),
                    "percepcion_tipo": self.perception_type,
                    "percepcion_base_imponible": cstr(self.perception_base),
                    "total_percepcion": cstr(self.total_perception),
                    "total_incluido_percepcion": cstr(self.total_with_perception),
                    "retencion_tipo": self.withholding_type,
                    "retencion_base_imponible": cstr(self.withholding_base),
                    "total_retencion": cstr(self.total_retention),
                    "total_impuestos_bolsas": cstr(self.total_plastic_bag_tax),
                    "detraccion": bool(cint(self.subject_to_detraction)),
                    "tipo_de_nota_de_credito": cstr(self.credit_note_reason),
                    "tipo_de_nota_de_debito": cstr(self.debit_note_reason),
                    "condiciones_de_pago": self.payment_terms,
                    "medio_de_pago": self.payment_method,
                    "placa_vehiculo": self.vehicle_license_plate,
                    "orden_compra_servicio": self.purchase_order,
                    "observaciones": self.remarks,
                    "codigo_unico": self.name,
                    "generado_por_contingencia": bool(
                        cint(self.generated_by_contingency)
                    ),
                    "bienes_region_selva": bool(cint(self.goods_from_jungle)),
                    "servicios_region_selva": bool(cint(self.services_from_jungle)),
                }
            )
        )

        if cstr(self.document_type) in {"3", "4"}:
            payload.update(
                {
                    "documento_que_se_modifica_tipo": cstr(self.base_document_type),
                    "documento_que_se_modifica_serie": self.base_document_series,
                    "documento_que_se_modifica_numero": cstr(self.base_document_number),
                }
            )

        if self.delivery_references:
            payload["guias"] = [
                apply_raw_payload_overrides(
                    {
                        "guia_tipo": cstr(row.guide_type),
                        "guia_serie_numero": row.guide_series_number,
                    },
                    row.raw,
                    f"delivery references row #{row.idx}",
                )
                for row in self.delivery_references
            ]

        if self.credit_installments:
            payload["venta_al_credito"] = [
                apply_raw_payload_overrides(
                    {
                        "cuota": cstr(row.installment_number),
                        "fecha_de_pago": to_nubefact_date(row.payment_date),
                        "importe": cstr(row.amount),
                    },
                    row.raw,
                    f"credit installments row #{row.idx}",
                )
                for row in self.credit_installments
            ]

        return apply_raw_payload_overrides(payload, self.raw, "invoice")

    def _validate_required_fields(self):
        require_fields(
            self,
            REQUIRED_FIELDS,
            "Required fields are missing for Invoice submission.",
        )

        if not self.items:
            frappe.throw("At least one item is required for Invoice submission.")

        self._validate_required_child_rows(self.items, ITEM_REQUIRED_FIELDS, "Items")
        self._validate_required_child_rows(
            self.delivery_references,
            DELIVERY_REFERENCE_REQUIRED_FIELDS,
            "Delivery Guides",
        )
        self._validate_required_child_rows(
            self.credit_installments,
            PAYMENT_INSTALLMENT_REQUIRED_FIELDS,
            "Credit Sale Installments",
        )

        if cstr(self.document_type) in {"3", "4"}:
            require_fields(
                self,
                NOTE_REFERENCE_REQUIRED_FIELDS,
                "Credit/Debit notes require modified document reference fields.",
            )

        if cstr(self.document_type) == "3":
            require_fields(
                self,
                CREDIT_NOTE_REQUIRED_FIELDS,
                "Credit notes require a reason.",
            )

        if cstr(self.document_type) == "4":
            require_fields(
                self,
                DEBIT_NOTE_REQUIRED_FIELDS,
                "Debit notes require a reason.",
            )

    def _validate_required_child_rows(
        self,
        rows: list[Document] | None,
        required_fields: list[str],
        table_label: str,
    ):
        for index, row in enumerate(rows or [], start=1):
            require_child_fields(
                row,
                required_fields,
                f"{table_label} row #{index} has missing required fields.",
            )

    def _extract_response_values(self, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        accepted_by_sunat = 1 if response.get("aceptada_por_sunat") else 0
        number = response.get("numero") or self.number
        title = self._compose_title(number)

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

    def _extract_void_response_values(self, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        ticket = cstr(
            response.get("ticket")
            or response.get("ticket_numero")
            or response.get("numero_ticket")
            or ""
        )
        accepted = 1 if response.get("aceptada_por_sunat") else 0

        return {
            "voided": 1 if accepted else 0,
            "void_date": now_datetime().date(),
            "void_ticket": ticket,
            "void_status": "Accepted" if accepted else "Pending",
            "status": "Voided" if accepted else self.status,
            "sunat_response_code": cstr(response.get("sunat_responsecode") or ""),
            "sunat_response_message": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "error_message": cstr(response.get("sunat_soap_error") or ""),
            "last_sunat_check": now_datetime(),
        }


@frappe.whitelist()
def send_to_nubefact(name: str):
    doc = frappe.get_doc("Nubefact Invoice", name)
    doc.check_permission("write")

    if doc.status not in {"Draft", "Error"}:
        frappe.throw("Only Draft or Error invoices can be sent to Nubefact.")

    try:
        doc.run_method("validate")

        values = _request_extract_and_save_response(
            doc,
            payload=doc._build_generate_payload(),
        )
    except Exception as exc:
        frappe.db.rollback()
        error_message = cstr(exc)
        values = {
            "status": "Error",
            "accepted_by_sunat": 0,
            "last_sunat_check": now_datetime(),
            "error_message": error_message,
        }

    if values and values.get("status") == "Error":
        _save_response_status(doc, values)
        frappe.db.commit()

    return values


@frappe.whitelist()
def refresh_sunat_status(name: str):
    doc = frappe.get_doc("Nubefact Invoice", name)
    doc.check_permission("read")
    return _refresh_sunat_status_doc(doc)


@frappe.whitelist()
def void_in_nubefact(name: str, reason: str):
    doc = frappe.get_doc("Nubefact Invoice", name)
    doc.check_permission("write")

    if doc.status not in {"Accepted", "Pending Response"}:
        frappe.throw("Only Accepted or Pending Response invoices can be voided.")

    if cint(doc.voided):
        frappe.throw("This invoice is already voided.")

    if not cstr(reason or "").strip():
        frappe.throw("A void reason is required.")

    if not doc.number:
        frappe.throw("Cannot void invoice because document number is missing.")

    try:
        response = make_request(
            payload={
                "operacion": "generar_anulacion",
                "tipo_de_comprobante": cint(doc.document_type),
                "serie": doc.series,
                "numero": cstr(doc.number),
                "motivo": reason,
                "codigo_unico": doc.name,
            },
            branch=doc.branch,
            reference_invoice=doc.name,
        )
        values = doc._extract_void_response_values(response)
        if values:
            values["void_reason"] = reason
            _save_response_status(doc, values)
    except Exception as exc:
        frappe.db.rollback()
        values = {
            "status": "Error",
            "error_message": cstr(exc),
            "void_status": "Rejected",
            "last_sunat_check": now_datetime(),
        }
        _save_response_status(doc, values)

    frappe.db.commit()
    return values


def poll_pending_invoices():
    pending_names = frappe.get_all(
        "Nubefact Invoice",
        filters={"status": "Pending Response", "accepted_by_sunat": 0},
        pluck="name",
        limit=20,
        order_by="modified asc",
    )

    for name in pending_names:
        try:
            doc = frappe.get_doc("Nubefact Invoice", name)
            _refresh_sunat_status_doc(doc)
        except Exception:
            frappe.log_error(
                title=f"Nubefact Invoice SUNAT refresh failed: {name}",
                message=frappe.get_traceback(),
            )


def _request_extract_and_save_response(
    doc: NubefactInvoice, payload: dict[str, Any]
) -> dict[str, Any]:
    response = make_request(
        payload=payload,
        branch=doc.branch,
        reference_invoice=doc.name,
    )
    values = doc._extract_response_values(response)

    if values:
        _save_response_status(doc, values)

    return values


def _refresh_sunat_status_doc(doc: NubefactInvoice) -> dict[str, Any]:

    if not doc.number:
        frappe.throw("Cannot refresh SUNAT status because document number is missing.")

    return _request_extract_and_save_response(
        doc,
        payload={
            "operacion": "consultar_comprobante",
            "tipo_de_comprobante": cint(doc.document_type),
            "serie": doc.series,
            "numero": cstr(doc.number),
        },
    )


def _save_response_status(
    doc: NubefactInvoice, values: dict[str, Any]
) -> dict[str, Any]:
    if not values:
        return {}

    cleared_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES)
    cleared_values.update(values)

    doc.update(cleared_values)
    doc.title = doc._compose_title()

    doc.db_update()
    doc.notify_update()

    return cleared_values
