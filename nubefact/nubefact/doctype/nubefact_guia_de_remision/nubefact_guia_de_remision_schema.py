from __future__ import annotations

"""Guía de Remisión Electrónica (GRE).

Referencias GRE API:
- Cabecera: gre-api-estructura-cabecera.md
- Ítems: gre-api-estructura-items.md
- Documentos relacionados: gre-api-estructura-documentos-relacionados.md
- Vehículos secundarios: gre-api-estructura-vehiculos-secundarios.md
- Conductores secundarios: gre-api-estructura-conductores-secundarios.md

Ruta: references/nubefact-docs/NUBEFACT DOC API JSON V1.md
"""


# Required for all GRE guides (type 7 and type 8)
REQUIRED_FIELDS = [
	"tipo_de_comprobante",
	"serie",
	"numero",
	"fecha_de_emision",
	"cliente_tipo_de_documento",
	"cliente_numero_de_documento",
	"cliente_denominacion",
	"cliente_direccion",
	"peso_bruto_total",
	"peso_bruto_unidad_de_medida",
	"fecha_de_inicio_de_traslado",
	"transportista_placa_numero",
	"punto_de_partida_ubigeo",
	"punto_de_partida_direccion",
	"punto_de_llegada_ubigeo",
	"punto_de_llegada_direccion",
]

# Required only for GRE Remitente (type 7)
TYPE_7_REQUIRED_FIELDS = [
	"motivo_de_traslado",
	"tipo_de_transporte",
	"numero_de_bultos",
]

# Required for GRE Remitente with public transport (transport_type = "01")
PUBLIC_TRANSPORT_REQUIRED_FIELDS = [
	"fecha_de_entrega_al_transportista",
	"transportista_documento_tipo",
	"transportista_documento_numero",
	"transportista_denominacion",
]

# Required for GRE Remitente with private transport (transport_type = "02") and for all GRE Transportista (type 8)
DRIVER_REQUIRED_FIELDS = [
	"conductor_documento_tipo",
	"conductor_documento_numero",
	"conductor_nombre",
	"conductor_apellidos",
	"conductor_numero_licencia",
]

# Required only for GRE Transportista (type 8)
TYPE_8_RECIPIENT_REQUIRED_FIELDS = [
	"destinatario_documento_tipo",
	"destinatario_documento_numero",
	"destinatario_denominacion",
]

ITEM_REQUIRED_FIELDS = ["unidad_de_medida", "descripcion", "cantidad"]

RELATED_DOCUMENT_REQUIRED_FIELDS = ["tipo", "serie", "numero"]

SECONDARY_VEHICLE_REQUIRED_FIELDS = ["placa_numero"]

SECONDARY_DRIVER_REQUIRED_FIELDS = [
	"documento_tipo",
	"documento_numero",
	"nombre",
	"apellidos",
	"numero_licencia",
]

SUBCONTRACTOR_REQUIRED_FIELDS = [
	"subcontratador_documento_tipo",
	"subcontratador_documento_numero",
	"subcontratador_denominacion",
]

SERVICE_PAYER_REQUIRED_FIELDS = [
	"pagador_servicio_documento_tipo_identidad",
	"pagador_servicio_documento_numero_identidad",
	"pagador_servicio_denominacion",
]

ESTABLISHMENT_REQUIRED_FIELDS = [
	"punto_de_partida_codigo_establecimiento_sunat",
	"punto_de_llegada_codigo_establecimiento_sunat",
]

DOCUMENT_TYPES = {"6", "1", "4", "7", "A", "0"}
DRIVER_DOCUMENT_TYPES = {"1", "4", "7", "A", "0"}
TRANSFER_REASONS = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "13", "14", "17", "18"}
TYPE_7_SUNAT_INDICATORS = {"04", "05", "06", "07"}
TYPE_8_SUNAT_INDICATORS = {"01", "02", "03", "04", "05"}
RELATED_DOCUMENT_CODES = {"50", "52"}
MAX_SECONDARY_ROWS = 2
