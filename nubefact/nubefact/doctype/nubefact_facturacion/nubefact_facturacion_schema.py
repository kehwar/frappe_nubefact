from __future__ import annotations

"""Comprobante electrónico de pago (factura, boleta, nota de crédito, nota de débito).

Referencias CPE API:
- Cabecera: cpe-api-estructura-cabecera.md
- Ítems: cpe-api-estructura-items.md
- Guías relacionadas: cpe-api-estructura-guias.md
- Cuotas (venta al crédito): cpe-api-estructura-venta-credito.md

Ruta: .agents/skills/nubefact-api-implementation/references/
"""

REQUIRED_FIELDS = [
    "tipo_de_comprobante",
    "serie",
    "fecha_de_emision",
    "cliente_tipo_de_documento",
    "cliente_numero_de_documento",
    "cliente_denominacion",
    "cliente_direccion",
    "moneda",
    "porcentaje_de_igv",
    "total_igv",
    "total",
]

ITEM_REQUIRED_FIELDS = [
    "unidad_de_medida",
    "descripcion",
    "cantidad",
    "valor_unitario",
    "precio_unitario",
    "subtotal",
    "tipo_de_igv",
    "igv",
    "total",
]

DELIVERY_REFERENCE_REQUIRED_FIELDS = ["guia_tipo", "guia_serie_numero"]

PAYMENT_INSTALLMENT_REQUIRED_FIELDS = ["cuota", "fecha_de_pago", "importe"]

NOTE_REFERENCE_REQUIRED_FIELDS = [
    "documento_que_se_modifica_tipo",
    "documento_que_se_modifica_serie",
    "documento_que_se_modifica_numero",
]

CREDIT_NOTE_REQUIRED_FIELDS = ["tipo_de_nota_de_credito"]
DEBIT_NOTE_REQUIRED_FIELDS = ["tipo_de_nota_de_debito"]
