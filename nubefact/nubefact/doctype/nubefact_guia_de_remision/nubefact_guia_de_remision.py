# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import cint, cstr, now_datetime

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_schema import (
    DRIVER_REQUIRED_FIELDS,
    ITEM_REQUIRED_FIELDS,
    PUBLIC_TRANSPORT_REQUIRED_FIELDS,
    RELATED_DOCUMENT_REQUIRED_FIELDS,
    REQUIRED_FIELDS,
    SECONDARY_DRIVER_REQUIRED_FIELDS,
    SECONDARY_VEHICLE_REQUIRED_FIELDS,
    TYPE_7_REQUIRED_FIELDS,
    TYPE_8_RECIPIENT_REQUIRED_FIELDS,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import (
    get_last_used_local_for_user,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import (
    get_origin_values as get_local_origin_values,
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
    "pdf_zip_base64": "",
    "xml_zip_base64": "",
    "cdr_zip_base64": "",
}


class NubefactGuiaDeRemision(Document):
    """Guía de Remisión Electrónica (GRE).

    Referencias GRE API:
    - Cabecera: gre-api-estructura-cabecera.md
    - Ítems: gre-api-estructura-items.md
    - Documentos relacionados: gre-api-estructura-documentos-relacionados.md
    - Vehículos secundarios: gre-api-estructura-vehiculos-secundarios.md
    - Conductores secundarios: gre-api-estructura-conductores-secundarios.md
    - Respuesta de consulta: gre-api-estructura-respuesta.md

    Ruta: .agents/skills/nubefact-api-implementation/references/
    """

    def autoname(self):
        series_prefix = f"GRE-{frappe.utils.now_datetime().strftime('%Y')}-"
        self.name = series_prefix + getseries(
            f"NubefactGuiaDeRemision::{series_prefix}", 6
        )

    def before_validate(self):
        if not self.status:
            self.status = "Borrador"

        self._set_inferred_values()

    def validate(self):

        if not cint(getattr(self, "skip_field_validation", 0)):
            self._validate_required_fields()

    def _set_inferred_values(self):
        if not cstr(self.local or "").strip():
            last_local = get_last_used_local_for_user(
                doctype=self.doctype,
                user=frappe.session.user,
                exclude_name=self.name,
            )

            if last_local:
                self.local = last_local

        local_origin_values = get_local_origin_values(self.local)
        inferred_origin_fields = (
            (
                "punto_de_partida_ubigeo",
                local_origin_values.get("punto_de_partida_ubigeo"),
            ),
            (
                "punto_de_partida_direccion",
                local_origin_values.get("punto_de_partida_direccion"),
            ),
            (
                "punto_de_partida_codigo_establecimiento_sunat",
                local_origin_values.get(
                    "punto_de_partida_codigo_establecimiento_sunat"
                ),
            ),
        )

        for fieldname, inferred_value in inferred_origin_fields:
            if not cstr(self.get(fieldname) or "").strip() and inferred_value:
                self.set(fieldname, inferred_value)

        self.title = self._compose_title()

    def _compose_title(self, numero: Any | None = None) -> str:
        serie = cstr(self.serie or "").strip()
        numero_texto = (
            cstr((self.numero if numero is None else numero) or "").strip().zfill(6)
        )
        return f"{serie}-{numero_texto}" if (serie or numero_texto) else ""

    def _build_generate_payload(self) -> dict[str, Any]:
        items_payload = [
            apply_raw_payload_overrides(
                omit_empty_values(
                    {
                        "unidad_de_medida": row.unidad_de_medida,
                        "codigo": row.codigo,
                        "descripcion": row.descripcion,
                        "cantidad": cstr(row.cantidad),
                        "codigo_dam": row.codigo_dam,
                    }
                ),
                row.custom,
                f"items fila #{row.idx}",
            )
            for row in self.items
        ]

        payload: dict[str, Any] = {
            "operacion": "generar_guia",
            "tipo_de_comprobante": cint(self.tipo_de_comprobante),
            "serie": self.serie,
            "cliente_tipo_de_documento": cstr(self.cliente_tipo_de_documento),
            "cliente_numero_de_documento": self.cliente_numero_de_documento,
            "cliente_denominacion": self.cliente_denominacion,
            "cliente_direccion": self.cliente_direccion,
            "fecha_de_emision": to_nubefact_date(self.fecha_de_emision),
            "fecha_de_inicio_de_traslado": to_nubefact_date(
                self.fecha_de_inicio_de_traslado
            ),
            "motivo_de_traslado": cstr(self.motivo_de_traslado),
            "peso_bruto_total": cstr(self.peso_bruto_total),
            "peso_bruto_unidad_de_medida": self.peso_bruto_unidad_de_medida,
            "numero_de_bultos": cstr(self.numero_de_bultos),
            "tipo_de_transporte": cstr(self.tipo_de_transporte),
            "punto_de_partida_ubigeo": self.punto_de_partida_ubigeo,
            "punto_de_partida_direccion": self.punto_de_partida_direccion,
            "punto_de_llegada_ubigeo": self.punto_de_llegada_ubigeo,
            "punto_de_llegada_direccion": self.punto_de_llegada_direccion,
            "enviar_automaticamente_al_cliente": (
                "true" if cint(self.enviar_automaticamente_al_cliente) else "false"
            ),
            "formato_de_pdf": cstr(self.formato_de_pdf or ""),
            "items": items_payload,
        }

        payload.update(
            omit_empty_values(
                {
                    "numero": self.numero,
                    "cliente_email": self.cliente_email,
                    "cliente_email_1": self.cliente_email_1,
                    "cliente_email_2": self.cliente_email_2,
                    "observaciones": self.observaciones,
                    "motivo_de_traslado_otros_descripcion": self.motivo_de_traslado_otros_descripcion,
                    "documento_relacionado_codigo": self.documento_relacionado_codigo,
                    "punto_de_partida_codigo_establecimiento_sunat": self.punto_de_partida_codigo_establecimiento_sunat,
                    "punto_de_llegada_codigo_establecimiento_sunat": self.punto_de_llegada_codigo_establecimiento_sunat,
                    "transportista_documento_tipo": self.transportista_documento_tipo,
                    "transportista_documento_numero": self.transportista_documento_numero,
                    "transportista_denominacion": self.transportista_denominacion,
                    "transportista_placa_numero": self.transportista_placa_numero,
                    "tuc_vehiculo_principal": self.tuc_vehiculo_principal,
                    "conductor_documento_tipo": self.conductor_documento_tipo,
                    "conductor_documento_numero": self.conductor_documento_numero,
                    "conductor_denominacion": self.conductor_denominacion,
                    "conductor_nombre": self.conductor_nombre,
                    "conductor_apellidos": self.conductor_apellidos,
                    "conductor_numero_licencia": self.conductor_numero_licencia,
                    "mtc": self.mtc,
                    "sunat_envio_indicador": self.sunat_envio_indicador,
                    "subcontratador_documento_tipo": self.subcontratador_documento_tipo,
                    "subcontratador_documento_numero": self.subcontratador_documento_numero,
                    "subcontratador_denominacion": self.subcontratador_denominacion,
                    "pagador_servicio_documento_tipo_identidad": self.pagador_servicio_documento_tipo_identidad,
                    "pagador_servicio_documento_numero_identidad": self.pagador_servicio_documento_numero_identidad,
                    "pagador_servicio_denominacion": self.pagador_servicio_denominacion,
                }
            )
        )

        if cstr(self.tipo_de_comprobante) == "8":
            payload["destinatario_documento_tipo"] = cstr(
                self.destinatario_documento_tipo
            )
            payload["destinatario_documento_numero"] = (
                self.destinatario_documento_numero
            )
            payload["destinatario_denominacion"] = self.destinatario_denominacion

        if self.documento_relacionado:
            payload["documento_relacionado"] = [
                apply_raw_payload_overrides(
                    {
                        "tipo": cstr(row.tipo),
                        "serie": row.serie,
                        "numero": cstr(row.numero),
                    },
                    row.custom,
                    f"documento relacionado fila #{row.idx}",
                )
                for row in self.documento_relacionado
            ]

        if self.vehiculos_secundarios:
            payload["vehiculos_secundarios"] = []
            for row in self.vehiculos_secundarios:
                vehicle = {"placa_numero": row.placa_numero}
                vehicle.update(omit_empty_values({"tuc": row.tuc}))
                payload["vehiculos_secundarios"].append(
                    apply_raw_payload_overrides(
                        vehicle,
                        row.custom,
                        f"vehículo secundario fila #{row.idx}",
                    )
                )

        if self.conductores_secundarios:
            payload["conductores_secundarios"] = [
                apply_raw_payload_overrides(
                    {
                        "documento_tipo": cstr(row.documento_tipo),
                        "documento_numero": row.documento_numero,
                        "nombre": row.nombre,
                        "apellidos": row.apellidos,
                        "numero_licencia": row.numero_licencia,
                    },
                    row.custom,
                    f"conductor secundario fila #{row.idx}",
                )
                for row in self.conductores_secundarios
            ]

        return apply_raw_payload_overrides(payload, self.custom, "guía")

    def _validate_required_fields(self):
        require_fields(
            self,
            REQUIRED_FIELDS,
            "Faltan campos obligatorios para enviar la guía de remisión.",
        )

        if not self.items:
            frappe.throw(
                "Se requiere al menos un ítem para enviar la guía de remisión."
            )

        self._validate_required_child_rows(self.items, ITEM_REQUIRED_FIELDS, "Ítems")
        self._validate_required_child_rows(
            self.documento_relacionado,
            RELATED_DOCUMENT_REQUIRED_FIELDS,
            "Documentos relacionados",
        )
        self._validate_required_child_rows(
            self.vehiculos_secundarios,
            SECONDARY_VEHICLE_REQUIRED_FIELDS,
            "Vehículos secundarios",
        )
        self._validate_required_child_rows(
            self.conductores_secundarios,
            SECONDARY_DRIVER_REQUIRED_FIELDS,
            "Conductores secundarios",
        )

        if cstr(self.tipo_de_comprobante) == "7":
            require_fields(
                self,
                TYPE_7_REQUIRED_FIELDS,
                "Motivo de traslado, tipo de transporte y número de bultos son obligatorios para GRE Remitente.",
            )

            if cstr(self.tipo_de_transporte) == "01":
                require_fields(
                    self,
                    PUBLIC_TRANSPORT_REQUIRED_FIELDS,
                    "Los campos del transportista son obligatorios para transporte público.",
                )
            elif cstr(self.tipo_de_transporte) == "02":
                require_fields(
                    self,
                    DRIVER_REQUIRED_FIELDS,
                    "Los campos del conductor son obligatorios para transporte privado.",
                )

        if cstr(self.tipo_de_comprobante) == "8":
            require_fields(
                self,
                TYPE_8_RECIPIENT_REQUIRED_FIELDS,
                "Los campos del destinatario son obligatorios para GRE Transportista.",
            )
            require_fields(
                self,
                DRIVER_REQUIRED_FIELDS,
                "Los campos del conductor son obligatorios para GRE Transportista.",
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
                f"{table_label} fila #{index} tiene campos obligatorios faltantes.",
            )

    def _extract_response_values(self, response: Any) -> dict[str, Any]:
        if not isinstance(response, dict):
            return {}

        aceptada_por_sunat = 1 if response.get("aceptada_por_sunat") else 0
        numero = response.get("numero") or self.numero
        title = self._compose_title(numero)

        return {
            "numero": numero,
            "title": title,
            "status": "Aceptada" if aceptada_por_sunat else "Pendiente de Aceptacion",
            "aceptada_por_sunat": aceptada_por_sunat,
            "last_sunat_check": now_datetime(),
            "sunat_responsecode": cstr(response.get("sunat_responsecode") or ""),
            "sunat_description": cstr(response.get("sunat_description") or ""),
            "sunat_note": cstr(response.get("sunat_note") or ""),
            "sunat_soap_error": cstr(response.get("sunat_soap_error") or ""),
            "error_message": cstr(response.get("sunat_soap_error") or ""),
            "enlace": cstr(response.get("enlace") or ""),
            "enlace_del_pdf": cstr(response.get("enlace_del_pdf") or ""),
            "enlace_del_xml": cstr(response.get("enlace_del_xml") or ""),
            "enlace_del_cdr": cstr(response.get("enlace_del_cdr") or ""),
            "cadena_para_codigo_qr": cstr(response.get("cadena_para_codigo_qr") or ""),
            "pdf_zip_base64": cstr(response.get("pdf_zip_base64") or ""),
            "xml_zip_base64": cstr(response.get("xml_zip_base64") or ""),
            "cdr_zip_base64": cstr(response.get("cdr_zip_base64") or ""),
        }


@frappe.whitelist()
def enviar_a_nubefact(name: str):

    doc = frappe.get_doc("Nubefact Guia De Remision", name)
    doc.check_permission("write")

    if doc.status not in {"Borrador", "Error"}:
        frappe.throw("Solo se pueden enviar guías en estado Borrador o Error.")

    try:
        doc._action = "save"
        doc.run_before_save_methods()

        values = _request_extract_and_save_response(
            doc,
            payload=doc._build_generate_payload(),
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
def refrescar_estado_sunat(name: str):
    doc = frappe.get_doc("Nubefact Guia De Remision", name)
    doc.check_permission("read")
    return _refresh_sunat_status_doc(doc)


def consultar_guias_pendientes():
    pending_names = frappe.get_all(
        "Nubefact Guia De Remision",
        filters={"status": "Pendiente de Aceptacion", "aceptada_por_sunat": 0},
        pluck="name",
        limit=20,
        order_by="modified asc",
    )

    for name in pending_names:
        try:
            doc = frappe.get_doc("Nubefact Guia De Remision", name)
            _refresh_sunat_status_doc(doc)
        except Exception:
            frappe.log_error(
                title=f"Nubefact Guia De Remision: falló refresco SUNAT ({name})",
                message=frappe.get_traceback(),
            )


def _request_extract_and_save_response(
    doc: NubefactGuiaDeRemision, payload: dict[str, Any]
) -> dict[str, Any]:
    response = make_request(
        payload=payload,
        local=doc.local,
        referencia_guia_de_remision=doc.name,
    )
    values = doc._extract_response_values(response)

    if values:
        _save_response_status(doc, values)

    return values


def _refresh_sunat_status_doc(doc: NubefactGuiaDeRemision) -> dict[str, Any]:

    if not doc.numero:
        frappe.throw(
            "No se puede consultar el estado SUNAT porque falta el número del documento."
        )

    return _request_extract_and_save_response(
        doc,
        payload={
            "operacion": "consultar_guia",
            "tipo_de_comprobante": cint(doc.tipo_de_comprobante),
            "serie": doc.serie,
            "numero": cstr(doc.numero),
        },
    )


def _save_response_status(
    doc: NubefactGuiaDeRemision, values: dict[str, Any]
) -> dict[str, Any]:
    if not values:
        return {}

    cleared_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES)
    cleared_values.update(values)

    doc.update(cleared_values)
    doc.db_set(cleared_values, update_modified=True)
    frappe.db.commit()

    return cleared_values
