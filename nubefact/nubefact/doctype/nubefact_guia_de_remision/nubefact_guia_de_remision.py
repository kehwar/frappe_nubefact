# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import (
	add_days,
	cint,
	cstr,
	get_datetime,
	getdate,
	now_datetime,
	nowdate,
	validate_email_address,
)

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_schema import (
	DOCUMENT_TYPES,
	DRIVER_DOCUMENT_TYPES,
	DRIVER_REQUIRED_FIELDS,
	ESTABLISHMENT_REQUIRED_FIELDS,
	GRE_DOCUMENT_TYPES,
	GROSS_WEIGHT_UNITS,
	ITEM_REQUIRED_FIELDS,
	MAX_SECONDARY_ROWS,
	PUBLIC_TRANSPORT_REQUIRED_FIELDS,
	RELATED_DOCUMENT_CODES,
	RELATED_DOCUMENT_REQUIRED_FIELDS,
	REQUIRED_FIELDS,
	SECONDARY_DRIVER_REQUIRED_FIELDS,
	SECONDARY_VEHICLE_REQUIRED_FIELDS,
	SERVICE_PAYER_REQUIRED_FIELDS,
	SUBCONTRACTOR_REQUIRED_FIELDS,
	TRANSFER_REASONS,
	TRANSPORT_TYPES,
	TYPE_7_REQUIRED_FIELDS,
	TYPE_7_SUNAT_INDICATORS,
	TYPE_8_RECIPIENT_REQUIRED_FIELDS,
	TYPE_8_SUNAT_INDICATORS,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import (
	get_last_used_local_for_user,
)
from nubefact.nubefact.doctype.nubefact_local.nubefact_local import (
	get_origin_values as get_local_origin_values,
)
from nubefact.nubefact.doctype.nubefact_series.nubefact_series import (
	advance_document_number_after_nubefact_duplicate,
	allocate_document_number,
	apply_and_validate_document_series,
	make_gre_artifact_names,
	set_company_from_local,
	validate_document_is_not_being_issued,
	validate_document_issuance_lease,
)
from nubefact.utils import (
	MAX_DUPLICATE_NUMBER_SKIPS,
	NUBEFACT_BASE64_FIELDS,
	NUBEFACT_DUPLICATE_DOCUMENT_ERROR_CODE,
	NubefactAPIError,
	apply_raw_payload_overrides,
	enqueue_nubefact_file_downloads,
	make_request,
	omit_empty_values,
	require_child_fields,
	require_fields,
	to_nubefact_date,
)

HISTORICAL_IMPORT_CAPABILITY = object()

_MANUAL_VOID_STATUSES = {"Anulación Solicitada", "Anulada"}
_MANUAL_VOID_AUDIT_FIELDS = (
	"anulado",
	"fecha_de_solicitud_de_anulacion",
	"anulacion_solicitada_por",
	"motivo_de_anulacion",
	"motivo_de_reversion_de_anulacion",
	"fecha_de_reversion_de_anulacion",
	"anulacion_revertida_por",
	"fecha_de_anulacion",
	"anulado_por",
)

_CLEARED_RESPONSE_VALUES: dict[str, Any] = {
	"aceptada_por_sunat": 0,
	"last_sunat_check": None,
	"sunat_responsecode": "",
	"sunat_description": "",
	"sunat_note": "",
	"sunat_soap_error": "",
	"nota_importante": "",
	"error_message": "",
	"enlace": "",
	"enlace_del_pdf": "",
	"enlace_del_xml": "",
	"enlace_del_cdr": "",
	"cadena_para_codigo_qr": "",
	"codigo_hash": "",
	"codigo_de_barras": "",
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

	Ruta: references/nubefact-docs/NUBEFACT DOC API JSON V1.md
	"""

	def autoname(self):
		series_prefix = f"GRE-{frappe.utils.now_datetime().strftime('%Y')}-"
		self.name = series_prefix + getseries(f"NubefactGuiaDeRemision::{series_prefix}", 6)

	def before_validate(self):
		validate_document_is_not_being_issued(self)
		if not self.status:
			self.status = "Borrador"

		self._set_inferred_values()

	def validate(self):
		self._validate_migration_fields()
		self._validate_manual_void_updates()
		if self._is_historical_import():
			self._validate_historical_import()
		elif not cint(getattr(self, "skip_field_validation", 0)):
			self._validate_required_fields()
			self._validate_document_rules()

	def _is_historical_import(self) -> bool:
		return self.flags.get("nubefact_historical_import") is HISTORICAL_IMPORT_CAPABILITY

	def _validate_migration_fields(self):
		if self._is_historical_import():
			return
		previous = self.get_doc_before_save()
		if not previous and not self.is_new():
			previous = frappe.db.get_value(
				self.doctype,
				self.name,
				["migrated_from_nubefact", "migration_job", "issued_identity_hash"],
				as_dict=True,
			)
		if previous and cint(previous.migrated_from_nubefact) and not self._is_historical_import():
			frappe.throw("Las GRE migradas son inmutables y se conservan para auditoría.")
		if not previous:
			if (
				cint(self.migrated_from_nubefact)
				or cstr(self.migration_job or "").strip()
				or cstr(self.issued_identity_hash or "").strip()
			):
				frappe.throw(
					"Los campos de migración solo pueden ser administrados por el proceso de migración."
				)
			return
		if cint(previous.migrated_from_nubefact) != cint(self.migrated_from_nubefact) or any(
			cstr(previous.get(fieldname) or "") != cstr(self.get(fieldname) or "")
			for fieldname in ("migration_job", "issued_identity_hash")
		):
			frappe.throw("La procedencia y la identidad emitida de la GRE son inmutables.")

	def _validate_historical_import(self):
		if cstr(self.tipo_de_comprobante) != "7":
			frappe.throw("La migración histórica solo admite GRE Remitente tipo 7.")
		if not re.fullmatch(r"T[A-Z0-9]{3}", cstr(self.serie).strip().upper()):
			frappe.throw("La serie histórica debe tener formato Txxx.")
		if not 1 <= cint(self.numero) <= 99_999_999:
			frappe.throw("El número histórico no es válido.")
		require_fields(
			self,
			["company", "local", "nubefact_series", "migration_job", "issued_identity_hash"],
			"La GRE histórica no contiene su identidad controlada completa.",
		)
		# Reuse the complete business/catalog validator and bypass only the rule
		# that ties an issuance request to today's date.
		self._validate_required_fields(historical_source=True)
		self._validate_document_rules(validate_issue_window=False, historical_source=True)

	def on_trash(self):
		migrated = cint(self.migrated_from_nubefact) or cint(
			frappe.db.get_value(self.doctype, self.name, "migrated_from_nubefact")
		)
		if migrated:
			frappe.throw("Las GRE migradas no se pueden eliminar; consérvelas para auditoría.")

	def _validate_manual_void_updates(self):
		"""Require the audited RPC actions for every manual-void state change."""

		previous = self.get_doc_before_save()
		if previous:
			status_changed = self.status != previous.status and bool(
				{self.status, previous.status} & _MANUAL_VOID_STATUSES
			)
			audit_changed = any(
				self.get(fieldname) != previous.get(fieldname) for fieldname in _MANUAL_VOID_AUDIT_FIELDS
			)
		else:
			status_changed = self.status in _MANUAL_VOID_STATUSES
			audit_changed = any(self.get(fieldname) for fieldname in _MANUAL_VOID_AUDIT_FIELDS)

		if status_changed or audit_changed:
			frappe.throw(
				"Los estados y datos de anulación solo pueden cambiarse mediante las acciones de anulación."
			)

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

		local_origin_values = {} if self._is_historical_import() else get_local_origin_values(self.local)
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
				local_origin_values.get("punto_de_partida_codigo_establecimiento_sunat"),
			),
		)

		for fieldname, inferred_value in inferred_origin_fields:
			if not cstr(self.get(fieldname) or "").strip() and inferred_value:
				self.set(fieldname, inferred_value)

		self.title = self._compose_title()

	def _compose_title(self, numero: Any | None = None) -> str:
		serie = cstr(self.serie or "").strip()
		raw_number = cstr((self.numero if numero is None else numero) or "").strip()
		numero_texto = raw_number.zfill(6) if raw_number else ""
		return f"{serie}-{numero_texto}" if (serie or numero_texto) else ""

	def _build_generate_payload(self) -> dict[str, Any]:
		document_type = cstr(self.tipo_de_comprobante)
		transport_type = cstr(self.tipo_de_transporte)
		motive = cstr(self.motivo_de_traslado).strip()
		indicator = cstr(self.sunat_envio_indicador).strip()
		item_unit_codes = self._get_item_unit_codes(motive)
		items_payload = [
			apply_raw_payload_overrides(
				omit_empty_values(
					{
						"unidad_de_medida": item_unit_codes[cstr(row.unidad_de_medida).strip()],
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
			"tipo_de_comprobante": cint(document_type),
			"serie": self.serie,
			"numero": self.numero,
			"cliente_tipo_de_documento": cstr(self.cliente_tipo_de_documento),
			"cliente_numero_de_documento": self.cliente_numero_de_documento,
			"cliente_denominacion": self.cliente_denominacion,
			"cliente_direccion": self.cliente_direccion,
			"fecha_de_emision": to_nubefact_date(self.fecha_de_emision),
			"fecha_de_inicio_de_traslado": to_nubefact_date(self.fecha_de_inicio_de_traslado),
			"peso_bruto_total": cstr(self.peso_bruto_total),
			"peso_bruto_unidad_de_medida": self.peso_bruto_unidad_de_medida,
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
					"cliente_email": self.cliente_email,
					"cliente_email_1": self.cliente_email_1,
					"cliente_email_2": self.cliente_email_2,
					"observaciones": self.observaciones,
					"punto_de_partida_codigo_establecimiento_sunat": self.punto_de_partida_codigo_establecimiento_sunat,
					"punto_de_llegada_codigo_establecimiento_sunat": self.punto_de_llegada_codigo_establecimiento_sunat,
					"mtc": self.mtc,
					"sunat_envio_indicador": indicator,
				}
			)
		)
		if indicator != "06" and (
			self._requires_vehicle_plate() or cstr(self.transportista_placa_numero).strip()
		):
			payload["transportista_placa_numero"] = self.transportista_placa_numero

		if document_type == "7":
			payload.update(
				{
					"motivo_de_traslado": motive,
					"numero_de_bultos": cstr(self.numero_de_bultos),
					"tipo_de_transporte": transport_type,
				}
			)
			if motive == "13":
				payload["motivo_de_traslado_otros_descripcion"] = self.motivo_de_traslado_otros_descripcion
			if motive in {"08", "09"}:
				payload["documento_relacionado_codigo"] = self.documento_relacionado_codigo
			if transport_type == "01":
				payload.update(
					{
						"fecha_de_entrega_al_transportista": to_nubefact_date(
							self.fecha_de_entrega_al_transportista
						),
						"transportista_documento_tipo": cstr(self.transportista_documento_tipo),
						"transportista_documento_numero": self.transportista_documento_numero,
						"transportista_denominacion": self.transportista_denominacion,
					}
				)
			elif transport_type == "02" and indicator != "06":
				payload.update(self._build_driver_payload())

		if document_type == "8":
			if indicator != "06":
				payload.update(self._build_driver_payload())
			payload.update(
				{
					"destinatario_documento_tipo": cstr(self.destinatario_documento_tipo),
					"destinatario_documento_numero": self.destinatario_documento_numero,
					"destinatario_denominacion": self.destinatario_denominacion,
				}
			)
			payload.update(omit_empty_values({"tuc_vehiculo_principal": self.tuc_vehiculo_principal}))
			if self.fecha_de_entrega_al_transportista:
				payload["fecha_de_entrega_al_transportista"] = to_nubefact_date(
					self.fecha_de_entrega_al_transportista
				)

		if indicator == "02":
			payload.update(
				{
					"subcontratador_documento_tipo": cstr(self.subcontratador_documento_tipo),
					"subcontratador_documento_numero": self.subcontratador_documento_numero,
					"subcontratador_denominacion": self.subcontratador_denominacion,
				}
			)
		elif indicator == "03":
			payload.update(
				{
					"pagador_servicio_documento_tipo_identidad": cstr(
						self.pagador_servicio_documento_tipo_identidad
					),
					"pagador_servicio_documento_numero_identidad": self.pagador_servicio_documento_numero_identidad,
					"pagador_servicio_denominacion": self.pagador_servicio_denominacion,
				}
			)

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
				if document_type == "8":
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

	def _get_item_unit_codes(self, motive: str) -> dict[str, str]:
		unit_codes = {cstr(row.unidad_de_medida).strip() for row in self.items or []}
		if not unit_codes:
			return {}
		if motive not in {"08", "09"}:
			return {code: code for code in unit_codes}

		mapped_codes = {
			row.name: cstr(row.codigo_importacion_exportacion).strip()
			for row in frappe.get_all(
				"Nubefact Unidad de Medida",
				filters={"name": ["in", sorted(unit_codes)]},
				fields=["name", "codigo_importacion_exportacion"],
			)
		}
		missing_codes = sorted(code for code in unit_codes if not mapped_codes.get(code))
		if missing_codes:
			frappe.throw(
				"Las siguientes unidades no tienen código para importación/exportación: "
				+ ", ".join(missing_codes)
			)
		return mapped_codes

	def _build_driver_payload(self) -> dict[str, Any]:
		return omit_empty_values(
			{
				"conductor_documento_tipo": cstr(self.conductor_documento_tipo),
				"conductor_documento_numero": self.conductor_documento_numero,
				"conductor_denominacion": self.conductor_denominacion,
				"conductor_nombre": self.conductor_nombre,
				"conductor_apellidos": self.conductor_apellidos,
				"conductor_numero_licencia": self.conductor_numero_licencia,
			}
		)

	def _validate_required_fields(self, *, historical_source: bool = False):
		require_fields(
			self,
			REQUIRED_FIELDS,
			"Faltan campos obligatorios para enviar la guía de remisión.",
		)

		indicator = cstr(self.sunat_envio_indicador).strip()
		if self._requires_vehicle_plate():
			require_fields(
				self,
				["transportista_placa_numero"],
				"La placa del vehículo es obligatoria para transporte privado y GRE Transportista, salvo traslados M1L.",
			)

		if not self.items:
			frappe.throw("Se requiere al menos un ítem para enviar la guía de remisión.")

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
				public_transport_fields = PUBLIC_TRANSPORT_REQUIRED_FIELDS
				if historical_source:
					public_transport_fields = [
						fieldname
						for fieldname in public_transport_fields
						if fieldname != "fecha_de_entrega_al_transportista"
					]
				require_fields(
					self,
					public_transport_fields,
					"Los datos del transportista son obligatorios para transporte público.",
				)
			elif cstr(self.tipo_de_transporte) == "02" and indicator != "06":
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
			if indicator != "06":
				require_fields(
					self,
					DRIVER_REQUIRED_FIELDS,
					"Los campos del conductor son obligatorios para GRE Transportista.",
				)

	def _validate_document_rules(
		self, *, validate_issue_window: bool = True, historical_source: bool = False
	):
		document_type = cstr(self.tipo_de_comprobante)
		if document_type not in GRE_DOCUMENT_TYPES:
			frappe.throw("El tipo de comprobante no pertenece al catálogo GRE de NubeFact.")
		if cstr(self.peso_bruto_unidad_de_medida) not in GROSS_WEIGHT_UNITS:
			frappe.throw("La unidad del peso bruto debe ser KGM o TNE.")
		if document_type == "7" and cstr(self.tipo_de_transporte) not in TRANSPORT_TYPES:
			frappe.throw("El tipo de transporte no pertenece al catálogo GRE de NubeFact.")

		expected_prefix = "T" if document_type == "7" else "V"
		series = cstr(self.serie).strip()
		if not re.fullmatch(rf"{expected_prefix}[A-Z0-9]{{3}}", series):
			frappe.throw(
				f"La serie debe tener 4 caracteres, empezar con {expected_prefix} y usar solo mayúsculas o números."
			)

		number_text = cstr(self.numero).strip()
		number = cint(self.numero)
		if number_text and not (number == 0 and self.nubefact_series):
			if number < 1 or number > 99_999_999:
				frappe.throw("El número debe ser un entero de 1 a 8 dígitos, sin ceros a la izquierda.")

		issue_date = getdate(self.fecha_de_emision)
		if validate_issue_window:
			allowed_issue_dates = {getdate(nowdate()), getdate(add_days(nowdate(), -1))}
			if issue_date not in allowed_issue_dates:
				frappe.throw("La fecha de emisión debe ser hoy o, como máximo, un día anterior.")
		if getdate(self.fecha_de_inicio_de_traslado) < issue_date:
			frappe.throw("La fecha de inicio del traslado no puede ser anterior a la fecha de emisión.")
		if (
			self.fecha_de_entrega_al_transportista
			and getdate(self.fecha_de_entrega_al_transportista) < issue_date
		):
			frappe.throw("La fecha de entrega al transportista no puede ser anterior a la fecha de emisión.")

		if cstr(self.cliente_tipo_de_documento) not in DOCUMENT_TYPES:
			frappe.throw("El tipo de documento del cliente no pertenece al catálogo de NubeFact.")
		self._validate_text_length("cliente_numero_de_documento", 1, 15)
		self._validate_text_length("cliente_denominacion", 1, 100)
		self._validate_text_length("cliente_direccion", 1, 100)
		self._validate_text_length("observaciones", 0, 1000)
		for fieldname in ("cliente_email", "cliente_email_1", "cliente_email_2"):
			email = cstr(self.get(fieldname)).strip()
			if email and (len(email) > 250 or not validate_email_address(email)):
				frappe.throw(
					f"{self.meta.get_label(fieldname)} debe ser un email válido de hasta 250 caracteres."
				)

		self._validate_positive_decimal("peso_bruto_total", integer_digits=12, decimal_digits=10)
		if document_type == "7":
			motive = cstr(self.motivo_de_traslado)
			if motive not in TRANSFER_REASONS:
				frappe.throw("El motivo de traslado no pertenece al catálogo GRE de NubeFact.")
			if not 1 <= cint(self.numero_de_bultos) <= 999_999:
				frappe.throw("El número de bultos debe ser un entero positivo de hasta 6 dígitos.")
			if motive == "13":
				require_fields(
					self,
					["motivo_de_traslado_otros_descripcion"],
					"La descripción es obligatoria cuando el motivo de traslado es Otros.",
				)
				description = cstr(self.motivo_de_traslado_otros_descripcion).strip()
				if len(description) > 70 or not re.fullmatch(r"[^\W_]+(?: [^\W_]+)*", description):
					frappe.throw(
						"La descripción de Otros debe ser alfanumérica, con espacios simples y hasta 70 caracteres."
					)
			if motive in {"08", "09"}:
				require_fields(
					self,
					["documento_relacionado_codigo"],
					"El código DAM o DS es obligatorio para importación o exportación.",
				)
				if cstr(self.documento_relacionado_codigo) not in RELATED_DOCUMENT_CODES:
					frappe.throw("El código de documento relacionado debe ser 50 (DAM) o 52 (DS).")
			if motive in {"04", "18"}:
				require_fields(
					self,
					ESTABLISHMENT_REQUIRED_FIELDS,
					"Los códigos de establecimiento SUNAT son obligatorios para este motivo de traslado.",
				)

		indicator = cstr(self.sunat_envio_indicador).strip()
		allowed_indicators = TYPE_7_SUNAT_INDICATORS if document_type == "7" else TYPE_8_SUNAT_INDICATORS
		if indicator and indicator not in allowed_indicators:
			frappe.throw("El indicador SUNAT no es válido para este tipo de GRE.")
		if indicator == "02":
			require_fields(
				self,
				SUBCONTRACTOR_REQUIRED_FIELDS,
				"Los datos del subcontratador son obligatorios para el indicador 02.",
			)
		if indicator == "03":
			require_fields(
				self,
				SERVICE_PAYER_REQUIRED_FIELDS,
				"Los datos del pagador del servicio son obligatorios para el indicador 03.",
			)

		for fieldname in ESTABLISHMENT_REQUIRED_FIELDS:
			code = cstr(self.get(fieldname) or "").strip()
			if code and not re.fullmatch(r"[A-Z0-9]{4}", code):
				frappe.throw(f"{self.meta.get_label(fieldname)} debe tener 4 mayúsculas o números.")

		if indicator == "02":
			if cstr(self.subcontratador_documento_tipo) != "6" or not re.fullmatch(
				r"\d{11}", cstr(self.subcontratador_documento_numero).strip()
			):
				frappe.throw("El subcontratador debe tener tipo 6 y un RUC de 11 dígitos.")
			self._validate_text_length("subcontratador_denominacion", 1, 250)
		if indicator == "03":
			if cstr(self.pagador_servicio_documento_tipo_identidad) not in DOCUMENT_TYPES:
				frappe.throw("El tipo de documento del pagador no pertenece al catálogo de NubeFact.")
			self._validate_text_length("pagador_servicio_documento_numero_identidad", 1, 15)
			self._validate_text_length("pagador_servicio_denominacion", 1, 250)

		if document_type == "8":
			if cstr(self.destinatario_documento_tipo) not in DOCUMENT_TYPES:
				frappe.throw("El tipo de documento del destinatario no pertenece al catálogo de NubeFact.")
			self._validate_text_length("destinatario_documento_numero", 1, 15)
			self._validate_text_length("destinatario_denominacion", 1, 100)

		if document_type == "7" and cstr(self.tipo_de_transporte) == "01":
			if cstr(self.transportista_documento_tipo) != "6":
				frappe.throw("El tipo de documento del transportista debe ser 6 (RUC).")
			if not re.fullmatch(r"\d{11}", cstr(self.transportista_documento_numero).strip()):
				frappe.throw("El RUC del transportista debe tener 11 dígitos.")
			self._validate_text_length("transportista_denominacion", 1, 100)

		if indicator != "06" and (
			self._requires_vehicle_plate() or cstr(self.transportista_placa_numero).strip()
		):
			self._validate_plate(self.transportista_placa_numero, "Placa del vehículo principal")
		self._validate_optional_uppercase_code("tuc_vehiculo_principal", 10, 15)
		if not historical_source and document_type != "8" and cstr(self.tuc_vehiculo_principal).strip():
			frappe.throw("El TUC del vehículo principal sólo aplica a GRE Transportista.")
		self._validate_optional_uppercase_code("mtc", 1, 20)

		for fieldname in ("punto_de_partida_ubigeo", "punto_de_llegada_ubigeo"):
			if not re.fullmatch(r"\d{6}", cstr(self.get(fieldname)).strip()):
				frappe.throw(f"{self.meta.get_label(fieldname)} debe contener 6 dígitos.")
		self._validate_text_length("punto_de_partida_direccion", 1, 150)
		self._validate_text_length("punto_de_llegada_direccion", 1, 150)

		if cstr(self.formato_de_pdf).strip() not in {"", "A4", "TICKET"}:
			frappe.throw("El formato de PDF debe ser A4, TICKET o vacío.")

		self._validate_driver_rules(document_type)
		self._validate_child_rules(document_type, historical_source=historical_source)

	def _validate_driver_rules(self, document_type: str):
		driver_required = cstr(self.sunat_envio_indicador).strip() != "06" and (
			document_type == "8" or (document_type == "7" and cstr(self.tipo_de_transporte) == "02")
		)
		if not driver_required:
			return

		if cstr(self.conductor_documento_tipo) not in DRIVER_DOCUMENT_TYPES:
			frappe.throw("El tipo de documento del conductor no pertenece al catálogo de NubeFact.")
		self._validate_text_length("conductor_documento_numero", 1, 15)
		self._validate_text_length("conductor_denominacion", 0, 100)
		self._validate_text_length("conductor_nombre", 1, 250)
		self._validate_text_length("conductor_apellidos", 1, 250)
		self._validate_license(self.conductor_numero_licencia, "Licencia del conductor principal")

	def _validate_child_rules(self, document_type: str, *, historical_source: bool = False):
		if len(self.vehiculos_secundarios or []) > MAX_SECONDARY_ROWS:
			frappe.throw("Se permiten como máximo 2 vehículos secundarios.")
		if len(self.conductores_secundarios or []) > MAX_SECONDARY_ROWS:
			frappe.throw("Se permiten como máximo 2 conductores secundarios.")
		if (
			not historical_source
			and document_type == "7"
			and cstr(self.tipo_de_transporte) != "02"
			and self.conductores_secundarios
		):
			frappe.throw("Los conductores secundarios sólo aplican al transporte privado en GRE Remitente.")

		motive = cstr(self.motivo_de_traslado).strip() if document_type == "7" else ""
		if motive in {"08", "09"}:
			self._get_item_unit_codes(motive)
		related_code = cstr(self.documento_relacionado_codigo)
		dam_markers = {
			("08", "50"): "10",
			("08", "52"): "18",
			("09", "50"): "40",
			("09", "52"): "48",
		}
		expected_dam_marker = dam_markers.get((motive, related_code))

		for row in self.items or []:
			unit = cstr(row.unidad_de_medida).strip()
			if not re.fullmatch(r"[A-Z0-9]{2,5}", unit):
				frappe.throw(
					f"Ítems fila #{row.idx}: la unidad de medida debe tener 2 a 5 mayúsculas o números."
				)
			if len(cstr(row.codigo).strip()) > 250:
				frappe.throw(f"Ítems fila #{row.idx}: el código admite hasta 250 caracteres.")
			if len(cstr(row.descripcion).strip()) > 250:
				frappe.throw(f"Ítems fila #{row.idx}: la descripción admite hasta 250 caracteres.")
			self._validate_decimal_value(
				row.cantidad,
				f"Ítems fila #{row.idx}: cantidad",
				integer_digits=12,
				decimal_digits=10,
			)
			dam_code = cstr(row.codigo_dam).strip()
			if motive in {"08", "09"} and not dam_code:
				frappe.throw(f"Ítems fila #{row.idx}: el código DAM o DS es obligatorio.")
			if dam_code:
				match = re.fullmatch(r"\d{1,4}/\d{3}-\d{4}-(\d{2})-\d{6}", dam_code)
				if not match or (expected_dam_marker and match.group(1) != expected_dam_marker):
					frappe.throw(f"Ítems fila #{row.idx}: el código DAM o DS no tiene el formato esperado.")

		related_series_prefixes = {"01": "F", "03": "B", "09": "T", "31": "V"}
		for row in self.documento_relacionado or []:
			related_type = cstr(row.tipo)
			if related_type not in related_series_prefixes:
				frappe.throw(f"Documentos relacionados fila #{row.idx}: tipo no válido.")
			series = cstr(row.serie).strip()
			expected_prefix = related_series_prefixes[related_type]
			if not re.fullmatch(rf"{expected_prefix}[A-Z0-9]{{3}}", series):
				frappe.throw(
					f"Documentos relacionados fila #{row.idx}: la serie debe tener 4 caracteres y empezar con {expected_prefix}."
				)
			if not re.fullmatch(r"[1-9]\d{0,7}", cstr(row.numero).strip()):
				frappe.throw(
					f"Documentos relacionados fila #{row.idx}: el número debe tener 1 a 8 dígitos sin ceros iniciales."
				)

		for row in self.vehiculos_secundarios or []:
			self._validate_plate(row.placa_numero, f"Vehículos secundarios fila #{row.idx}: placa")
			tuc = cstr(row.tuc).strip()
			if tuc and document_type != "8" and not historical_source:
				frappe.throw("El TUC de vehículos secundarios sólo aplica a GRE Transportista.")
			if tuc and (not re.fullmatch(r"[A-Z0-9]{10,15}", tuc)):
				frappe.throw(f"Vehículos secundarios fila #{row.idx}: TUC no válido.")

		for row in self.conductores_secundarios or []:
			if cstr(row.documento_tipo) not in DRIVER_DOCUMENT_TYPES:
				frappe.throw(f"Conductores secundarios fila #{row.idx}: tipo de documento no válido.")
			if not 1 <= len(cstr(row.documento_numero).strip()) <= 15:
				frappe.throw(f"Conductores secundarios fila #{row.idx}: documento no válido.")
			if not 1 <= len(cstr(row.nombre).strip()) <= 250:
				frappe.throw(f"Conductores secundarios fila #{row.idx}: nombre no válido.")
			if not 1 <= len(cstr(row.apellidos).strip()) <= 250:
				frappe.throw(f"Conductores secundarios fila #{row.idx}: apellidos no válidos.")
			self._validate_license(row.numero_licencia, f"Conductores secundarios fila #{row.idx}: licencia")

	def _validate_text_length(self, fieldname: str, minimum: int, maximum: int):
		value = cstr(self.get(fieldname) or "").strip()
		if value and not minimum <= len(value) <= maximum:
			frappe.throw(
				f"{self.meta.get_label(fieldname)} debe tener entre {minimum} y {maximum} caracteres."
			)

	def _validate_positive_decimal(self, fieldname: str, *, integer_digits: int, decimal_digits: int):
		self._validate_decimal_value(
			self.get(fieldname),
			self.meta.get_label(fieldname),
			integer_digits=integer_digits,
			decimal_digits=decimal_digits,
		)

	def _validate_decimal_value(self, value: Any, label: str, *, integer_digits: int, decimal_digits: int):
		try:
			decimal_value = Decimal(cstr(value))
		except InvalidOperation:
			frappe.throw(f"{label} debe ser numérico.")
		if not decimal_value.is_finite() or decimal_value <= 0:
			frappe.throw(f"{label} debe ser mayor que cero.")
		_, digits, exponent = decimal_value.as_tuple()
		decimals = max(-exponent, 0)
		integers = max(len(digits) - decimals, 0)
		if integers > integer_digits or decimals > decimal_digits:
			frappe.throw(f"{label} admite hasta {integer_digits} enteros y {decimal_digits} decimales.")

	def _requires_vehicle_plate(self) -> bool:
		if cstr(self.sunat_envio_indicador).strip() == "06":
			return False
		document_type = cstr(self.tipo_de_comprobante)
		return document_type == "8" or (document_type == "7" and cstr(self.tipo_de_transporte) == "02")

	def _validate_plate(self, value: Any, label: str):
		plate = cstr(value).strip()
		if not re.fullmatch(r"[A-Z0-9]{6,8}", plate) or set(plate) <= {"0"}:
			frappe.throw(f"{label} debe tener 6 a 8 mayúsculas o números, sin guiones, y no puede ser cero.")

	def _validate_optional_uppercase_code(self, fieldname: str, minimum: int, maximum: int):
		value = cstr(self.get(fieldname) or "").strip()
		if value and (not re.fullmatch(r"[A-Z0-9]+", value) or not minimum <= len(value) <= maximum):
			frappe.throw(
				f"{self.meta.get_label(fieldname)} debe tener {minimum} a {maximum} mayúsculas o números, sin guiones."
			)

	def _validate_license(self, value: Any, label: str):
		if not re.fullmatch(r"[A-Z0-9]{9,10}", cstr(value).strip()):
			frappe.throw(f"{label} debe tener 9 a 10 mayúsculas o números.")

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

		response_type = response.get("tipo_de_comprobante")
		response_series = cstr(response.get("serie") or "").strip().upper()
		if response_type is not None and cint(response_type) != cint(self.tipo_de_comprobante):
			frappe.throw("La respuesta de NubeFact pertenece a otro tipo de comprobante.")
		if response_series and response_series != cstr(self.serie).strip().upper():
			frappe.throw("La respuesta de NubeFact pertenece a otra serie.")

		accepted_value = response.get("aceptada_por_sunat")
		aceptada_por_sunat = (
			1
			if accepted_value is True or accepted_value == 1 or cstr(accepted_value).strip().lower() == "true"
			else 0
		)
		numero = response.get("numero") or self.numero
		if self.numero and numero and cint(numero) != cint(self.numero):
			frappe.throw("La respuesta de NubeFact pertenece a otro número de guía.")
		title = self._compose_title(numero)

		sunat_responsecode = cstr(response.get("sunat_responsecode") or "").strip()
		sunat_description = cstr(response.get("sunat_description") or "").strip()
		sunat_note = cstr(response.get("sunat_note") or "").strip()
		sunat_soap_error = cstr(response.get("sunat_soap_error") or "").strip()
		# NubeFact does not document a terminal rejection flag. A non-zero SUNAT
		# response code or SOAP error is an explicit failure; free-text descriptions
		# and notes alone may accompany an asynchronous pending response.
		terminal_error = not aceptada_por_sunat and (
			bool(sunat_soap_error) or bool(sunat_responsecode and sunat_responsecode != "0")
		)
		error_message = (
			" - ".join(
				value
				for value in (
					sunat_responsecode,
					sunat_description,
					sunat_note,
					sunat_soap_error,
				)
				if value
			)
			if terminal_error
			else ""
		)

		values = {
			"numero": numero,
			"title": title,
			"status": (
				"Aceptada" if aceptada_por_sunat else "Error" if terminal_error else "Pendiente de Aceptacion"
			),
			"aceptada_por_sunat": aceptada_por_sunat,
			"last_sunat_check": now_datetime(),
			"sunat_responsecode": sunat_responsecode,
			"sunat_description": sunat_description,
			"sunat_note": sunat_note,
			"sunat_soap_error": sunat_soap_error,
			"error_message": error_message,
		}
		for fieldname in (
			"nota_importante",
			"enlace",
			"enlace_del_pdf",
			"enlace_del_xml",
			"enlace_del_cdr",
			"pdf_zip_base64",
			"xml_zip_base64",
			"cdr_zip_base64",
			"cadena_para_codigo_qr",
			"codigo_hash",
			"codigo_de_barras",
		):
			if fieldname in response:
				values[fieldname] = cstr(response.get(fieldname) or "")
		return values


@frappe.whitelist(methods=["POST"])
def enviar_a_nubefact(name: str):
	doc = frappe.get_doc("Nubefact Guia De Remision", name)
	doc.check_permission("write")
	if cint(doc.migrated_from_nubefact):
		frappe.throw("Una GRE migrada desde NubeFact no puede volver a emitirse.")
	frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(name,),
	)
	doc.reload()

	if cint(doc.migrated_from_nubefact):
		frappe.throw("Una GRE migrada desde NubeFact no puede volver a emitirse.")
	if doc.status not in {"Borrador", "Error"}:
		frappe.throw("Solo se pueden enviar guías en estado Borrador o Error.")

	number_was_unassigned = not cint(doc.numero)
	doc._action = "save"
	doc.run_before_save_methods()
	make_gre_artifact_names(doc.company, doc.tipo_de_comprobante, doc.serie, doc.numero or 1)
	allocate_document_number(doc, mark_as_issuing=True)
	# Persist the reservation before the external request. A timeout can hide
	# a successful issue, so an assigned number must never be reused.
	frappe.db.commit()
	issuance_modified = frappe.db.get_value(doc.doctype, doc.name, "modified")

	duplicate_numbers_skipped = 0
	try:
		while True:
			attempted_number = cint(doc.numero)
			payload = doc._build_generate_payload()
			request_identity_matches_document = (
				payload.get("operacion") == "generar_guia"
				and cstr(payload.get("tipo_de_comprobante")) == cstr(cint(doc.tipo_de_comprobante))
				and cstr(payload.get("serie")).strip() == cstr(doc.serie).strip()
				and cint(payload.get("numero")) == attempted_number
			)
			try:
				values = _request_extract_and_save_response(
					doc,
					payload=payload,
					clear_previous=True,
					expected_issuance_modified=issuance_modified,
				)
				break
			except NubefactAPIError as exc:
				can_skip_duplicate = (
					number_was_unassigned
					and request_identity_matches_document
					and exc.error_code == NUBEFACT_DUPLICATE_DOCUMENT_ERROR_CODE
					and duplicate_numbers_skipped < MAX_DUPLICATE_NUMBER_SKIPS
				)
				if not can_skip_duplicate:
					raise

				frappe.db.rollback()
				advance_document_number_after_nubefact_duplicate(
					doc,
					expected_number=attempted_number,
					expected_modified=issuance_modified,
				)
				frappe.db.commit()
				duplicate_numbers_skipped += 1
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
		try:
			validate_document_issuance_lease(doc, issuance_modified)
		except frappe.ValidationError:
			frappe.db.rollback()
		else:
			_save_response_status(doc, values)
			frappe.db.commit()

	return values


@frappe.whitelist(methods=["POST"])
def refrescar_estado_sunat(name: str):
	doc = frappe.get_doc("Nubefact Guia De Remision", name)
	doc.check_permission("write")
	return _refresh_sunat_status_doc(doc)


@frappe.whitelist(methods=["POST"])
def solicitar_anulacion(name: str, motivo: str) -> dict[str, Any]:
	"""Record a user's request to void an accepted GRE manually in SUNAT."""

	doc = frappe.get_doc("Nubefact Guia De Remision", name)
	doc.check_permission("write")
	frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(name,),
	)
	doc.reload()

	if doc.status != "Aceptada":
		frappe.throw("Solo se puede solicitar la anulación de una GRE en estado Aceptada.")

	motivo = cstr(motivo or "").strip()
	if not motivo:
		frappe.throw("Se requiere un motivo de anulación.")
	if len(motivo) > 500:
		frappe.throw("El motivo de anulación admite hasta 500 caracteres.")

	values = {
		"status": "Anulación Solicitada",
		"motivo_de_anulacion": motivo,
		"fecha_de_solicitud_de_anulacion": now_datetime(),
		"anulacion_solicitada_por": frappe.session.user,
		"motivo_de_reversion_de_anulacion": "",
		"fecha_de_reversion_de_anulacion": None,
		"anulacion_revertida_por": "",
		"anulado": 0,
		"fecha_de_anulacion": None,
		"anulado_por": "",
	}
	_persist_manual_void_transition(doc, values)
	return values


@frappe.whitelist(methods=["POST"])
def cancelar_solicitud_de_anulacion(name: str, motivo: str) -> dict[str, Any]:
	"""Let a manager reject a manual void request and restore the accepted state."""

	if not _has_nubefact_manager_role():
		frappe.throw(
			"Solo un Nubefact Manager puede cancelar una solicitud de anulación.",
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Nubefact Guia De Remision", name)
	doc.check_permission("write")
	frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(name,),
	)
	doc.reload()

	if doc.status != "Anulación Solicitada":
		frappe.throw("Solo una GRE con anulación solicitada puede volver al estado Aceptada.")

	motivo = cstr(motivo or "").strip()
	if not motivo:
		frappe.throw("Se requiere un motivo de reversión.")
	if len(motivo) > 500:
		frappe.throw("El motivo de reversión admite hasta 500 caracteres.")

	values = {
		"status": "Aceptada",
		"motivo_de_reversion_de_anulacion": motivo,
		"fecha_de_reversion_de_anulacion": now_datetime(),
		"anulacion_revertida_por": frappe.session.user,
	}
	_persist_manual_void_transition(doc, values)
	return values


@frappe.whitelist(methods=["POST"])
def marcar_como_anulada(name: str) -> dict[str, Any]:
	"""Let a manager confirm that a requested GRE was voided in the SUNAT portal."""

	if not _has_nubefact_manager_role():
		frappe.throw(
			"Solo un Nubefact Manager puede marcar una GRE como anulada.",
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Nubefact Guia De Remision", name)
	doc.check_permission("write")
	frappe.db.sql(
		"SELECT `name` FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(name,),
	)
	doc.reload()

	if doc.status != "Anulación Solicitada":
		frappe.throw("Solo una GRE con anulación solicitada puede marcarse como anulada.")

	values = {
		"status": "Anulada",
		"anulado": 1,
		"fecha_de_anulacion": now_datetime(),
		"anulado_por": frappe.session.user,
	}
	_persist_manual_void_transition(doc, values)
	return values


def _persist_manual_void_transition(doc: NubefactGuiaDeRemision, values: dict[str, Any]) -> None:
	"""Persist one state transition and retain it in the Version audit trail."""

	doc.db_set(values, update_modified=True)
	doc.save_version()
	frappe.db.commit()


def _has_nubefact_manager_role() -> bool:
	return bool({"Nubefact Manager", "System Manager"} & set(frappe.get_roles()))


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
	doc: NubefactGuiaDeRemision,
	payload: dict[str, Any],
	*,
	clear_previous: bool = False,
	expected_issuance_modified: Any = None,
	expected_response_modified: Any = None,
) -> dict[str, Any]:
	make_gre_artifact_names(doc.company, doc.tipo_de_comprobante, doc.serie, doc.numero)
	response = make_request(
		payload=payload,
		local=doc.local,
		referencia_guia_de_remision=doc.name,
		migration_job=doc.migration_job if cint(doc.migrated_from_nubefact) else None,
	)
	if not isinstance(response, dict) or not response:
		frappe.throw("NubeFact devolvió una respuesta vacía o inválida.")

	values = doc._extract_response_values(response)
	if not values:
		frappe.throw("No se pudo interpretar la respuesta de NubeFact.")

	if values:
		if expected_issuance_modified is not None:
			validate_document_issuance_lease(doc, expected_issuance_modified)
		saved_values = _save_response_status(
			doc,
			values,
			clear_previous=clear_previous,
			expected_modified=expected_response_modified,
		)
		enqueue_nubefact_file_downloads(
			doc.doctype,
			doc.name,
			doc.title or doc.name,
			values,
			request_payload=payload if payload.get("operacion") == "generar_guia" else None,
			response_payload=response if payload.get("operacion") == "generar_guia" else None,
		)

	return saved_values


def _refresh_sunat_status_doc(doc: NubefactGuiaDeRemision) -> dict[str, Any]:
	if doc.status in _MANUAL_VOID_STATUSES:
		frappe.throw("No se puede refrescar el estado SUNAT porque la anulación se gestiona manualmente.")
	if not doc.numero:
		frappe.throw("No se puede consultar el estado SUNAT porque falta el número del documento.")

	return _request_extract_and_save_response(
		doc,
		payload={
			"operacion": "consultar_guia",
			"tipo_de_comprobante": cint(doc.tipo_de_comprobante),
			"serie": doc.serie,
			"numero": cstr(doc.numero),
		},
		expected_response_modified=doc.modified,
	)


def _save_response_status(
	doc: NubefactGuiaDeRemision,
	values: dict[str, Any],
	*,
	clear_previous: bool = False,
	expected_modified: Any = None,
) -> dict[str, Any]:
	if not values:
		return {}

	saved_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES) if clear_previous else {}
	saved_values.update(
		{fieldname: value for fieldname, value in values.items() if fieldname not in NUBEFACT_BASE64_FIELDS}
	)

	# Serialize this write with manual cancellation. A SUNAT query started before
	# a request must not move the GRE back to Aceptada when its response arrives.
	current = frappe.db.sql(
		"SELECT `status`, `modified` FROM `tabNubefact Guia De Remision` WHERE `name` = %s FOR UPDATE",
		(doc.name,),
		as_dict=True,
	)[0]
	if expected_modified is not None and get_datetime(current.modified) != get_datetime(expected_modified):
		frappe.throw("La GRE cambió mientras se consultaba SUNAT; se descartó la respuesta anterior.")
	if current.status in _MANUAL_VOID_STATUSES:
		saved_values["status"] = current.status

	doc.update(saved_values)
	doc.db_set(saved_values, update_modified=True)
	frappe.db.commit()

	return saved_values
