# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import cint, cstr, now_datetime

from nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion_schema import (
    CREDIT_NOTE_REQUIRED_FIELDS,
    DEBIT_NOTE_REQUIRED_FIELDS,
    DELIVERY_REFERENCE_REQUIRED_FIELDS,
    ITEM_REQUIRED_FIELDS,
    NOTE_REFERENCE_REQUIRED_FIELDS,
    PAYMENT_INSTALLMENT_REQUIRED_FIELDS,
    REQUIRED_FIELDS,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import (
    get_last_used_local_for_user,
)
from nubefact.nubefact.doctype.nubefact_series.nubefact_series import (
    allocate_document_number,
    apply_and_validate_document_series,
    set_company_from_local,
    validate_document_is_not_being_issued,
)
from nubefact.utils import (
    NUBEFACT_BASE64_FIELDS,
    apply_raw_payload_overrides,
    enqueue_nubefact_file_downloads,
    make_request,
    omit_empty_values,
    require_child_fields,
    require_fields,
    to_nubefact_date,
)

_CLEARED_RESPONSE_VALUES: dict[str, Any] = {
    "aceptada_por_sunat": 0,
    "last_sunat_check": None,
    "sunat_responsecode": "",
    "sunat_description": "",
    "sunat_note": "",
    "sunat_soap_error": "",
    "error_message": "",
    "enlace": "",
    "enlace_del_pdf": "",
    "enlace_del_xml": "",
    "enlace_del_cdr": "",
    "cadena_para_codigo_qr": "",
    "codigo_hash": "",
    "codigo_de_barras": "",
    "sunat_ticket_numero": "",
}


class NubefactFacturacion(Document):
    """Comprobante electrónico de pago (factura, boleta, nota de crédito, nota de débito).

    Referencias CPE API:
    - Cabecera: cpe-api-estructura-cabecera.md
    - Ítems: cpe-api-estructura-items.md
    - Guías relacionadas: cpe-api-estructura-guias.md
    - Cuotas (venta al crédito): cpe-api-estructura-venta-credito.md
    - Respuesta de consulta: cpe-api-estructura-respuesta.md
    - Generacion de anulacion: cpe-api-estructura-anulacion-generar.md
    - Respuesta de anulacion: cpe-api-estructura-anulacion-respuesta.md

    Ruta: references/nubefact-docs/NUBEFACT DOC API JSON V1.md
    """

    def autoname(self):
        series_prefix = f"CPE-{frappe.utils.now_datetime().strftime('%Y')}-"
        self.name = series_prefix + getseries(
            f"NubefactFacturacion::{series_prefix}", 6
        )

    def before_validate(self):
        validate_document_is_not_being_issued(self)
        if not self.status:
            self.status = "Borrador"

        self._set_inferred_values()

    def validate(self):
        if not cint(getattr(self, "skip_field_validation", 0)):
            self._validate_required_fields()
            self._validate_document_identity()

    def _set_inferred_values(self):
        if cint(self.numero_asignado_automaticamente) and not self.nubefact_series:
            frappe.throw("La Serie NubeFact no puede eliminarse después de asignar el número.")

        if self.nubefact_series:
            apply_and_validate_document_series(self)
        else:
            if not cstr(self.local or "").strip():
                last_local = get_last_used_local_for_user(
                    doctype=self.doctype,
                    user=frappe.session.user,
                    exclude_name=self.name,
                )

                if last_local:
                    self.local = last_local

            set_company_from_local(self)

        self.title = self._compose_title()

    def _compose_title(self, number: Any | None = None) -> str:
        series = cstr(self.serie or "").strip()
        number_text = cstr((self.numero if number is None else number) or "").strip()
        return f"{series}-{number_text}" if (series or number_text) else ""

    def _build_generate_payload(self) -> dict[str, Any]:
        items_payload = [
            apply_raw_payload_overrides(
                omit_empty_values(
                    {
                        "unidad_de_medida": row.unidad_de_medida,
                        "codigo": row.codigo,
                        "codigo_producto_sunat": row.codigo_producto_sunat,
                        "descripcion": row.descripcion,
                        "cantidad": cstr(row.cantidad),
                        "valor_unitario": cstr(row.valor_unitario),
                        "precio_unitario": cstr(row.precio_unitario),
                        "descuento": cstr(row.descuento),
                        "subtotal": cstr(row.subtotal),
                        "tipo_de_igv": cstr(row.tipo_de_igv),
                        "tipo_de_ivap": cstr(row.tipo_de_ivap),
                        "igv": cstr(row.igv),
                        "impuesto_bolsas": cstr(row.impuesto_bolsas),
                        "total": cstr(row.total),
                        "anticipo_regularizacion": bool(
                            cint(row.anticipo_regularizacion)
                        ),
                        "anticipo_documento_serie": row.anticipo_documento_serie,
                        "anticipo_documento_numero": row.anticipo_documento_numero,
                        "tipo_de_isc": cstr(row.tipo_de_isc),
                        "isc": cstr(row.isc),
                    }
                ),
                row.custom,
                f"fila de ítems #{row.idx}",
            )
            for row in self.items
        ]

        payload: dict[str, Any] = {
            "operacion": "generar_comprobante",
            "tipo_de_comprobante": cint(self.tipo_de_comprobante),
            "serie": self.serie,
            "cliente_tipo_de_documento": cstr(self.cliente_tipo_de_documento),
            "cliente_numero_de_documento": self.cliente_numero_de_documento,
            "cliente_denominacion": self.cliente_denominacion,
            "cliente_direccion": self.cliente_direccion,
            "fecha_de_emision": to_nubefact_date(self.fecha_de_emision),
            "moneda": cstr(self.moneda),
            "porcentaje_de_igv": cstr(self.porcentaje_de_igv),
            "total_igv": cstr(self.total_igv),
            "total": cstr(self.total),
            "enviar_automaticamente_a_la_sunat": bool(
                cint(self.enviar_automaticamente_a_la_sunat)
            ),
            "enviar_automaticamente_al_cliente": bool(
                cint(self.enviar_automaticamente_al_cliente)
            ),
            "formato_de_pdf": cstr(self.formato_de_pdf or ""),
            "items": items_payload,
        }

        payload.update(
            omit_empty_values(
                {
                    "numero": self.numero,
                    "sunat_transaction": cstr(self.sunat_transaction),
                    "fecha_de_vencimiento": (
                        to_nubefact_date(self.fecha_de_vencimiento)
                        if self.fecha_de_vencimiento
                        else None
                    ),
                    "cliente_email": self.cliente_email,
                    "cliente_email_1": self.cliente_email_1,
                    "cliente_email_2": self.cliente_email_2,
                    "total_gravada": cstr(self.total_gravada),
                    "total_inafecta": cstr(self.total_inafecta),
                    "total_exonerada": cstr(self.total_exonerada),
                    "total_descuento": cstr(self.total_descuento),
                    "total_anticipo": cstr(self.total_anticipo),
                    "total_gratuita": cstr(self.total_gratuita),
                    "total_otros_cargos": cstr(self.total_otros_cargos),
                    "descuento_global": cstr(self.descuento_global),
                    "tipo_de_cambio": cstr(self.tipo_de_cambio),
                    "percepcion_tipo": self.percepcion_tipo,
                    "percepcion_base_imponible": cstr(self.percepcion_base_imponible),
                    "total_percepcion": cstr(self.total_percepcion),
                    "total_incluido_percepcion": cstr(self.total_incluido_percepcion),
                    "retencion_tipo": self.retencion_tipo,
                    "retencion_base_imponible": cstr(self.retencion_base_imponible),
                    "total_retencion": cstr(self.total_retencion),
                    "total_impuestos_bolsas": cstr(self.total_impuestos_bolsas),
                    "detraccion": bool(cint(self.detraccion)),
                    "tipo_de_nota_de_credito": cstr(self.tipo_de_nota_de_credito),
                    "tipo_de_nota_de_debito": cstr(self.tipo_de_nota_de_debito),
                    "condiciones_de_pago": self.condiciones_de_pago,
                    "medio_de_pago": self.medio_de_pago,
                    "placa_vehiculo": self.placa_vehiculo,
                    "orden_compra_servicio": self.orden_compra_servicio,
                    "observaciones": self.observaciones,
                    "codigo_unico": self.codigo_unico or self.name,
                    "generado_por_contingencia": bool(
                        cint(self.generado_por_contingencia)
                    ),
                    "bienes_region_selva": bool(cint(self.bienes_region_selva)),
                    "servicios_region_selva": bool(cint(self.servicios_region_selva)),
                    "nubecont_tipo_de_venta_codigo": self.nubecont_tipo_de_venta_codigo,
                    "detraccion_tipo": cstr(self.detraccion_tipo),
                    "detraccion_total": cstr(self.detraccion_total),
                    "detraccion_porcentaje": cstr(self.detraccion_porcentaje),
                    "medio_de_pago_detraccion": cstr(self.medio_de_pago_detraccion),
                    "ubigeo_origen": self.ubigeo_origen,
                    "direccion_origen": self.direccion_origen,
                    "ubigeo_destino": self.ubigeo_destino,
                    "direccion_destino": self.direccion_destino,
                    "detalle_viaje": self.detalle_viaje,
                    "val_ref_serv_trans": cstr(self.val_ref_serv_trans),
                    "val_ref_carga_efec": cstr(self.val_ref_carga_efec),
                    "val_ref_carga_util": cstr(self.val_ref_carga_util),
                    "punto_origen_viaje": self.punto_origen_viaje,
                    "punto_destino_viaje": self.punto_destino_viaje,
                    "descripcion_tramo": self.descripcion_tramo,
                    "val_ref_carga_efec_tramo_virtual": cstr(
                        self.val_ref_carga_efec_tramo_virtual
                    ),
                    "configuracion_vehicular": self.configuracion_vehicular,
                    "carga_util_tonel_metricas": cstr(self.carga_util_tonel_metricas),
                    "carga_efec_tonel_metricas": cstr(self.carga_efec_tonel_metricas),
                    "val_ref_tonel_metrica": cstr(self.val_ref_tonel_metrica),
                    "val_pre_ref_carga_util_nominal": cstr(
                        self.val_pre_ref_carga_util_nominal
                    ),
                    "indicador_aplicacion_retorno_vacio": bool(
                        cint(self.indicador_aplicacion_retorno_vacio)
                    ),
                    "matricula_emb_pesquera": self.matricula_emb_pesquera,
                    "nombre_emb_pesquera": self.nombre_emb_pesquera,
                    "descripcion_tipo_especie_vendida": self.descripcion_tipo_especie_vendida,
                    "lugar_de_descarga": self.lugar_de_descarga,
                    "cantidad_especie_vendida": cstr(self.cantidad_especie_vendida),
                    "fecha_de_descarga": (
                        to_nubefact_date(self.fecha_de_descarga)
                        if self.fecha_de_descarga
                        else None
                    ),
                }
            )
        )

        if cstr(self.tipo_de_comprobante) in {"3", "4"}:
            payload.update(
                {
                    "documento_que_se_modifica_tipo": cstr(
                        self.documento_que_se_modifica_tipo
                    ),
                    "documento_que_se_modifica_serie": self.documento_que_se_modifica_serie,
                    "documento_que_se_modifica_numero": cstr(
                        self.documento_que_se_modifica_numero
                    ),
                }
            )

        if self.guias:
            payload["guias"] = [
                apply_raw_payload_overrides(
                    {
                        "guia_tipo": cstr(row.guia_tipo),
                        "guia_serie_numero": row.guia_serie_numero,
                    },
                    row.custom,
                    f"fila de guías relacionadas #{row.idx}",
                )
                for row in self.guias
            ]

        if self.venta_al_credito:
            payload["venta_al_credito"] = [
                apply_raw_payload_overrides(
                    {
                        "cuota": cstr(row.cuota),
                        "fecha_de_pago": to_nubefact_date(row.fecha_de_pago),
                        "importe": cstr(row.importe),
                    },
                    row.custom,
                    f"fila de cuotas de venta al crédito #{row.idx}",
                )
                for row in self.venta_al_credito
            ]

        return apply_raw_payload_overrides(payload, self.custom, "comprobante")

    def _validate_required_fields(self):
        require_fields(
            self,
            REQUIRED_FIELDS,
            "Faltan campos obligatorios para el envío del comprobante.",
        )

        if not self.items:
            frappe.throw("Se requiere al menos un ítem para el envío del comprobante.")

        self._validate_required_child_rows(self.items, ITEM_REQUIRED_FIELDS, "Ítems")
        self._validate_required_child_rows(
            self.guias,
            DELIVERY_REFERENCE_REQUIRED_FIELDS,
            "Guías de entrega",
        )
        self._validate_required_child_rows(
            self.venta_al_credito,
            PAYMENT_INSTALLMENT_REQUIRED_FIELDS,
            "Cuotas de venta al crédito",
        )

        if cstr(self.tipo_de_comprobante) in {"3", "4"}:
            require_fields(
                self,
                NOTE_REFERENCE_REQUIRED_FIELDS,
                "Las notas de crédito/débito requieren campos de referencia del documento modificado.",
            )

        if cstr(self.tipo_de_comprobante) == "3":
            require_fields(
                self,
                CREDIT_NOTE_REQUIRED_FIELDS,
                "Las notas de crédito requieren un motivo.",
            )

        if cstr(self.tipo_de_comprobante) == "4":
            require_fields(
                self,
                DEBIT_NOTE_REQUIRED_FIELDS,
                "Las notas de débito requieren un motivo.",
            )

    def _validate_document_identity(self):
        document_type = cstr(self.tipo_de_comprobante)
        series = cstr(self.serie).strip()
        allowed_prefixes = {"1": {"F"}, "2": {"B"}, "3": {"F", "B"}, "4": {"F", "B"}}
        if not re.fullmatch(r"[FB][A-Z0-9]{3}", series) or series[:1] not in allowed_prefixes.get(
            document_type, set()
        ):
            frappe.throw("La serie debe tener 4 caracteres y corresponder al tipo de comprobante.")

        number_text = cstr(self.numero).strip()
        number = cint(self.numero)
        if number_text and not (number == 0 and self.nubefact_series):
            if not 1 <= number <= 99_999_999:
                frappe.throw("El número debe ser un entero de 1 a 8 dígitos, sin ceros a la izquierda.")

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
                f"La fila #{index} de {table_label} tiene campos obligatorios faltantes.",
            )

    def _extract_response_values(self, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        response_type = response.get("tipo_de_comprobante")
        response_series = cstr(response.get("serie") or "").strip()
        response_number = response.get("numero")
        if response_type is not None and cint(response_type) != cint(self.tipo_de_comprobante):
            frappe.throw("La respuesta de NubeFact pertenece a otro tipo de comprobante.")
        if response_series and response_series != cstr(self.serie).strip():
            frappe.throw("La respuesta de NubeFact pertenece a otra serie.")
        if response_number and self.numero and cint(response_number) != cint(self.numero):
            frappe.throw("La respuesta de NubeFact pertenece a otro número de comprobante.")

        accepted_by_sunat = 1 if response.get("aceptada_por_sunat") else 0
        number = response_number or self.numero
        title = self._compose_title(number)

        values = {
            "numero": number,
            "title": title,
            "status": "Aceptada" if accepted_by_sunat else "Pendiente de Aceptación",
            "aceptada_por_sunat": accepted_by_sunat,
            "last_sunat_check": now_datetime(),
            "sunat_responsecode": cstr(response.get("sunat_responsecode") or ""),
            "sunat_description": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "error_message": cstr(response.get("sunat_soap_error") or ""),
            "sunat_ticket_numero": cstr(
                response.get("sunat_ticket_numero")
                or response.get("ticket")
                or response.get("ticket_numero")
                or response.get("numero_ticket")
                or ""
            ),
        }
        for fieldname in (
            "enlace",
            "enlace_del_pdf",
            "enlace_del_xml",
            "enlace_del_cdr",
            "cadena_para_codigo_qr",
            "pdf_zip_base64",
            "xml_zip_base64",
            "cdr_zip_base64",
            "codigo_hash",
            "codigo_de_barras",
        ):
            if fieldname in response:
                values[fieldname] = cstr(response.get(fieldname) or "")

        return values

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
            "anulado": 1 if accepted else 0,
            "fecha_de_anulacion": now_datetime().date(),
            "sunat_ticket_numero": ticket,
            "estado_de_anulacion": "Aceptada" if accepted else "Pendiente",
            "status": "Anulada" if accepted else self.status,
            "sunat_responsecode": cstr(response.get("sunat_responsecode") or ""),
            "sunat_description": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "error_message": cstr(response.get("sunat_soap_error") or ""),
            "last_sunat_check": now_datetime(),
        }


@frappe.whitelist()
def send_to_nubefact(name: str):
    doc = frappe.get_doc("Nubefact Facturacion", name)
    doc.check_permission("write")
    frappe.db.sql(
        "SELECT `name` FROM `tabNubefact Facturacion` WHERE `name` = %s FOR UPDATE",
        (name,),
    )
    doc.reload()

    if doc.status not in {"Borrador", "Error"}:
        frappe.throw(
            "Solo los comprobantes en estado Borrador o Error pueden enviarse a Nubefact."
        )

    doc._action = "save"
    doc.run_before_save_methods()
    allocate_document_number(doc, mark_as_issuing=True)
    # Persist the reservation before the external request. A timeout can hide
    # a successful issue, so an assigned number must never be reused.
    frappe.db.commit()

    try:
        values = _request_extract_and_save_response(
            doc,
            payload=doc._build_generate_payload(),
            clear_previous=True,
        )
    except Exception as exc:
        frappe.db.rollback()
        error_message = cstr(exc)
        values = {
            "status": "Error",
            "aceptada_por_sunat": 0,
            "last_sunat_check": now_datetime(),
            "error_message": error_message,
        }

    if values and values.get("status") == "Error":
        _save_response_status(doc, values)
        frappe.db.commit()

    return values


@frappe.whitelist()
def refresh_sunat_status(name: str):
    doc = frappe.get_doc("Nubefact Facturacion", name)
    doc.check_permission("read")
    return _refresh_sunat_status_doc(doc)


@frappe.whitelist()
def void_in_nubefact(name: str, reason: str):
    doc = frappe.get_doc("Nubefact Facturacion", name)
    doc.check_permission("write")

    if doc.status not in {"Aceptada", "Pendiente de Aceptacion"}:
        frappe.throw(
            "Solo los comprobantes en estado Aceptada o Pendiente de Aceptación pueden anularse."
        )

    if cint(doc.anulado):
        frappe.throw("Este comprobante ya está anulado.")

    if not cstr(reason or "").strip():
        frappe.throw("Se requiere un motivo de anulación.")

    if not doc.numero:
        frappe.throw(
            "No se puede anular el comprobante porque falta el número de documento."
        )

    try:
        response = make_request(
            payload={
                "operacion": "generar_anulacion",
                "tipo_de_comprobante": cint(doc.tipo_de_comprobante),
                "serie": doc.serie,
                "numero": cstr(doc.numero),
                "motivo": reason,
                "codigo_unico": doc.codigo_unico or doc.name,
            },
            local=doc.local,
            reference_invoice=doc.name,
        )
        values = doc._extract_void_response_values(response)
        if values:
            values["motivo"] = reason
            _save_response_status(doc, values)
    except Exception as exc:
        frappe.db.rollback()
        values = {
            "status": "Error",
            "error_message": cstr(exc),
            "estado_de_anulacion": "Rechazada",
            "last_sunat_check": now_datetime(),
        }
        _save_response_status(doc, values)

    frappe.db.commit()
    return values


def poll_pending_invoices():
    pending_names = frappe.get_all(
        "Nubefact Facturacion",
        filters={"status": "Pendiente de Aceptación", "aceptada_por_sunat": 0},
        pluck="name",
        limit=20,
        order_by="modified asc",
    )

    for name in pending_names:
        try:
            doc = frappe.get_doc("Nubefact Facturacion", name)
            _refresh_sunat_status_doc(doc)
        except Exception:
            frappe.log_error(
                title=f"Nubefact Facturacion: falló la actualización SUNAT para {name}",
                message=frappe.get_traceback(),
            )


def _request_extract_and_save_response(
    doc: NubefactFacturacion,
    payload: dict[str, Any],
    *,
    clear_previous: bool = False,
) -> dict[str, Any]:
    response = make_request(
        payload=payload,
        local=doc.local,
        reference_invoice=doc.name,
    )
    if not isinstance(response, dict) or not response:
        frappe.throw("NubeFact devolvió una respuesta vacía o inválida.")

    values = doc._extract_response_values(response)
    if not values:
        frappe.throw("No se pudo interpretar la respuesta de NubeFact.")

    if values:
        saved_values = _save_response_status(doc, values, clear_previous=clear_previous)
        enqueue_nubefact_file_downloads(
            doc.doctype,
            doc.name,
            doc.title or doc.name,
            values,
            request_payload=(
                payload if payload.get("operacion") == "generar_comprobante" else None
            ),
            response_payload=(
                response if payload.get("operacion") == "generar_comprobante" else None
            ),
        )

    return saved_values


def _refresh_sunat_status_doc(doc: NubefactFacturacion) -> dict[str, Any]:

    if not doc.numero:
        frappe.throw(
            "No se puede actualizar el estado SUNAT porque falta el número de documento."
        )

    return _request_extract_and_save_response(
        doc,
        payload={
            "operacion": "consultar_comprobante",
            "tipo_de_comprobante": cint(doc.tipo_de_comprobante),
            "serie": doc.serie,
            "numero": cstr(doc.numero),
        },
    )


def _save_response_status(
    doc: NubefactFacturacion,
    values: dict[str, Any],
    *,
    clear_previous: bool = False,
) -> dict[str, Any]:
    if not values:
        return {}

    saved_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES) if clear_previous else {}
    saved_values.update(
        {
            fieldname: value
            for fieldname, value in values.items()
            if fieldname not in NUBEFACT_BASE64_FIELDS
        }
    )

    doc.update(saved_values)
    doc.title = doc._compose_title()
    saved_values["title"] = doc.title

    doc.db_set(saved_values, update_modified=True)
    doc.notify_update()

    return saved_values
