# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.utils import add_days, cint, cstr, getdate, now_datetime, nowdate, validate_email_address

from nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision_schema import (
	DOCUMENT_TYPES,
	DRIVER_DOCUMENT_TYPES,
	DRIVER_REQUIRED_FIELDS,
	ESTABLISHMENT_REQUIRED_FIELDS,
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
from nubefact.utils import (
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
	"nota_importante": "",
	"error_message": "",
	"enlace": "",
	"enlace_del_pdf": "",
	"enlace_del_xml": "",
	"enlace_del_cdr": "",
	"pdf_zip_base64": "",
	"xml_zip_base64": "",
	"cdr_zip_base64": "",
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
		if not self.status:
			self.status = "Borrador"

		self._set_inferred_values()

	def validate(self):
		if not cint(getattr(self, "skip_field_validation", 0)):
			self._validate_required_fields()
			self._validate_document_rules()

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
				local_origin_values.get("punto_de_partida_codigo_establecimiento_sunat"),
			),
		)

		for fieldname, inferred_value in inferred_origin_fields:
			if not cstr(self.get(fieldname) or "").strip() and inferred_value:
				self.set(fieldname, inferred_value)

		self.title = self._compose_title()

	def _compose_title(self, numero: Any | None = None) -> str:
		serie = cstr(self.serie or "").strip()
		numero_texto = cstr((self.numero if numero is None else numero) or "").strip().zfill(6)
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

		document_type = cstr(self.tipo_de_comprobante)
		transport_type = cstr(self.tipo_de_transporte)
		motive = cstr(self.motivo_de_traslado)
		indicator = cstr(self.sunat_envio_indicador).strip()

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
			"transportista_placa_numero": self.transportista_placa_numero,
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
			elif transport_type == "02":
				payload.update(self._build_driver_payload())

		if document_type == "8":
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

	def _validate_required_fields(self):
		require_fields(
			self,
			REQUIRED_FIELDS,
			"Faltan campos obligatorios para enviar la guía de remisión.",
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

	def _validate_document_rules(self):
		document_type = cstr(self.tipo_de_comprobante)
		expected_prefix = "T" if document_type == "7" else "V"
		series = cstr(self.serie).strip()
		if not re.fullmatch(rf"{expected_prefix}[A-Z0-9]{{3}}", series):
			frappe.throw(
				f"La serie debe tener 4 caracteres, empezar con {expected_prefix} y usar solo mayúsculas o números."
			)

		number = cint(self.numero)
		if number < 1 or number > 99_999_999:
			frappe.throw("El número debe ser un entero de 1 a 8 dígitos, sin ceros a la izquierda.")

		issue_date = getdate(self.fecha_de_emision)
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

		self._validate_plate(self.transportista_placa_numero, "Placa del vehículo principal")
		self._validate_optional_uppercase_code("tuc_vehiculo_principal", 10, 15)
		if document_type != "8" and cstr(self.tuc_vehiculo_principal).strip():
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
		self._validate_child_rules(document_type)

	def _validate_driver_rules(self, document_type: str):
		driver_required = document_type == "8" or (
			document_type == "7" and cstr(self.tipo_de_transporte) == "02"
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

	def _validate_child_rules(self, document_type: str):
		if len(self.vehiculos_secundarios or []) > MAX_SECONDARY_ROWS:
			frappe.throw("Se permiten como máximo 2 vehículos secundarios.")
		if len(self.conductores_secundarios or []) > MAX_SECONDARY_ROWS:
			frappe.throw("Se permiten como máximo 2 conductores secundarios.")
		if document_type == "7" and cstr(self.tipo_de_transporte) != "02" and self.conductores_secundarios:
			frappe.throw("Los conductores secundarios sólo aplican al transporte privado en GRE Remitente.")

		motive = cstr(self.motivo_de_traslado) if document_type == "7" else ""
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
			if tuc and document_type != "8":
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
		response_series = cstr(response.get("serie") or "").strip()
		if response_type is not None and cint(response_type) != cint(self.tipo_de_comprobante):
			frappe.throw("La respuesta de NubeFact pertenece a otro tipo de comprobante.")
		if response_series and response_series != cstr(self.serie).strip():
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
	doc: NubefactGuiaDeRemision,
	payload: dict[str, Any],
	*,
	clear_previous: bool = False,
) -> dict[str, Any]:
	response = make_request(
		payload=payload,
		local=doc.local,
		referencia_guia_de_remision=doc.name,
	)
	values = doc._extract_response_values(response)

	if values:
		_save_response_status(doc, values, clear_previous=clear_previous)
		enqueue_nubefact_file_downloads(doc.doctype, doc.name, doc.title or doc.name, values)

	return values


def _refresh_sunat_status_doc(doc: NubefactGuiaDeRemision) -> dict[str, Any]:
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
	)


def _save_response_status(
	doc: NubefactGuiaDeRemision,
	values: dict[str, Any],
	*,
	clear_previous: bool = False,
) -> dict[str, Any]:
	if not values:
		return {}

	saved_values: dict[str, Any] = dict(_CLEARED_RESPONSE_VALUES) if clear_previous else {}
	saved_values.update(values)

	doc.update(saved_values)
	doc.db_set(saved_values, update_modified=True)
	frappe.db.commit()

	return saved_values
