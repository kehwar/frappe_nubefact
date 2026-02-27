# DocType Guide: Nubefact Invoice

This guide is for correctly filling `Nubefact Invoice` before sending to NubeFact (`generar_comprobante`).

Use this order:
1. Fill **Mandatory First** fields.
2. Fill **Conditionally Mandatory Next** based on scenario.
3. Fill **Optional / Enrichment** fields.
4. Validate totals and send.

`number` / `numero` is optional on send. If omitted, NubeFact auto-generates the next sequential number.

---

## Workflow by Sections

## 1) Document Header

### Mandatory First
- **Document identity**
  - `document_type` (`tipo_de_comprobante`)
  - `series` (`serie`)
- **SUNAT operation context**
  - `sunat_transaction`
- **Dates**
  - `issue_date` (`fecha_de_emision`)

### Conditionally Mandatory Next
- **Credit / Debit notes** (`document_type` = `3` or `4`)
  - `base_document_type` (`documento_que_se_modifica_tipo`)
  - `base_document_series` (`documento_que_se_modifica_serie`)
  - `base_document_number` (`documento_que_se_modifica_numero`)
- **Credit note reason** (`document_type` = `3`)
  - `credit_note_reason` (`tipo_de_nota_de_credito`)
- **Debit note reason** (`document_type` = `4`)
  - `debit_note_reason` (`tipo_de_nota_de_debito`)

### Optional / Enrichment
- `number` (`numero`) if you want to force a specific sequence (otherwise omit)
- `due_date`

---

## 2) Customer Data

### Mandatory First
- `client_document_type` (`cliente_tipo_de_documento`)
- `client_document_number` (`cliente_numero_de_documento`)
- `client_name` (`cliente_denominacion`)
- `client_address` (`cliente_direccion`)

### Conditionally Mandatory Next
- No extra conditional customer fields in canonical baseline.

### Optional / Enrichment
- `client_email`, `client_email_1`, `client_email_2`

---

## 3) Currency and Totals (Header)

### Mandatory First
- **Tax basis**
  - `currency` (`moneda`)
  - `igv_percentage` (`porcentaje_de_igv`)
- **Required totals**
  - `total_igv`
  - `total`

### Conditionally Mandatory Next
- **USD documents**
  - `exchange_rate` (`tipo_de_cambio`) when `currency = 2` (USD)
- **Perception flow**
  - `perception_type`, `perception_base`, `total_perception`, `total_with_perception`
- **Retention flow**
  - `withholding_type`, `withholding_base`, `total_retention`
- **Detraction flow** (`subject_to_detraction = 1`)
  - `detraction_type`, `detraction_total`, `detraction_percentage`, `detraction_payment_method`
  - Transport-specific detraction references when applicable (`origin_*`, `destination_*`, route/vehicle references)

### Optional / Enrichment
- `total_taxable`, `total_unaffected`, `total_exempt`
- `global_discount`, `total_discount`, `total_advance`, `total_free`, `total_other_charges`
- `total_plastic_bag_tax`, `total_isc`

---

## 4) Items Table (`items`)

### Mandatory First (per row)
- `uom` (`unidad_de_medida`)
- `item_code` (`codigo`)
- `description` (`descripcion`)
- `quantity` (`cantidad`)
- `unit_price` (`valor_unitario`)
- `unit_price_with_tax` (`precio_unitario`)
- `line_total` (`subtotal`)
- `igv_type` (`tipo_de_igv`)
- `igv`
- `line_total_with_tax` (`total`)

### Conditionally Mandatory Next
- **Downpayment regularization rows** (`downpayment_regularization = 1`)
  - `downpayment_document_series`
  - `downpayment_document_number`

### Optional / Enrichment
- `sunat_product_code`
- `discount`
- `ivap_type`
- `plastic_bag_tax`
- `isc_type`, `isc`

---

## 5) Related Guides and Credit Installments

### Mandatory First
- No mandatory rows unless your business scenario requires them.

### Conditionally Mandatory Next
- **When attaching delivery guides** (`delivery_references` table)
  - Per row: `guide_type`, `guide_series_number`
- **When sale is on credit** (`credit_installments` table)
  - Per row: `installment_number`, `payment_date`, `amount`

### Optional / Enrichment
- Additional guide references and installment rows as needed.

---

## 6) Operational Settings

### Mandatory First
- None.

### Conditionally Mandatory Next
- None.

### Optional / Enrichment
- `auto_send_to_sunat`
- `auto_send_to_client`
- `pdf_format`
- `generated_by_contingency`
- `goods_from_jungle`, `services_from_jungle`
- `payment_terms`, `payment_method`, `purchase_order`, `vehicle_license_plate`, `remarks`

---

## Pre-Send Validation Checklist

- At least one `items` row exists.
- Item sums are coherent with header totals (`total`, `total_igv`, and other totals used by scenario).
- Series prefix matches document type (`F*` Factura, `B*` Boleta).
- `sunat_transaction` is set and valid for the scenario.
- If `number` is omitted, confirm sequence should be API-assigned.
- Conditional blocks are complete (credit/debit reason, installments, detraction/perception/retention).

---

## Submission + Post-Submission

1. Build payload and call `generar_comprobante`.
2. Persist response values (`numero`, SUNAT status fields, links).
3. If needed, call `consultar_comprobante` to refresh status.
4. For voiding, use `generar_anulacion` only after document has a valid `series` + `number`.
