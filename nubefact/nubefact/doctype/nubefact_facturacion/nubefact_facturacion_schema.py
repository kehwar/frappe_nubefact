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
    "uom",
    "item_code",
    "description",
    "quantity",
    "unit_price",
    "unit_price_with_tax",
    "line_total",
    "igv_type",
    "igv",
    "line_total_with_tax",
]

DELIVERY_REFERENCE_REQUIRED_FIELDS = ["guide_type", "guide_series_number"]

PAYMENT_INSTALLMENT_REQUIRED_FIELDS = ["installment_number", "payment_date", "amount"]

NOTE_REFERENCE_REQUIRED_FIELDS = [
    "documento_que_se_modifica_tipo",
    "documento_que_se_modifica_serie",
    "documento_que_se_modifica_numero",
]

CREDIT_NOTE_REQUIRED_FIELDS = ["tipo_de_nota_de_credito"]
DEBIT_NOTE_REQUIRED_FIELDS = ["tipo_de_nota_de_debito"]
