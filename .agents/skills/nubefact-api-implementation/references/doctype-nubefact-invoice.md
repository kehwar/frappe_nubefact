# DocType: Nubefact Invoice

**DocType Name**: `Nubefact Invoice`
**Type**: Standard DocType
**Purpose**: Manages electronic invoices, receipts (boletas), credit notes, and debit notes via NubeFact JSON v1 API.

## Supported Document Types

- `1`: Factura
- `2`: Boleta
- `3`: Nota de Crédito
- `4`: Nota de Débito

## Manual / Asset Alignment Notes

- Model aligned to `generar_comprobante`, `consultar_comprobante`, and `generar_anulacion` examples in `assets/json-v1-*`.
- Includes credit/debit note reference fields and credit-sale installments.
- Includes SUNAT response and void/anulacion tracking fields.

## Main Fields

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| **Document Type** | | - | Section Break | | |
| Document Type | `document_type` | `tipo_de_comprobante` | Select | Yes* | Options: 1 (Factura), 2 (Boleta), 3 (Nota de Crédito), 4 (Nota de Débito) |
| Series | `series` | `serie` | Data | Yes* | 4-character series (F* for Factura, B* for Boleta) |
| Number | `number` | `numero` | Int | Yes* | Sequential document number |
| SUNAT Transaction Type | `sunat_transaction` | `sunat_transaction` | Select | No | SUNAT transaction code (1-35, including detraction/perception/tax-free codes) |
| | | - | Column Break | | |
| Issue Date | `issue_date` | `fecha_de_emision` | Date | Yes* | Date of document issuance |
| Due Date | `due_date` | `fecha_de_vencimiento` | Date | No | Payment due date |
| **Client Information** | | - | Section Break | | |
| Client Document Type | `client_document_type` | `cliente_tipo_de_documento` | Select | Yes* | Options include 6 (RUC), 1 (DNI), -, 4, 7, A, B, 0, G |
| Client Document Number | `client_document_number` | `cliente_numero_de_documento` | Data | Yes* | Client's identification number |
| Client Name | `client_name` | `cliente_denominacion` | Data | Yes* | Client's full name or business name |
| | | - | Column Break | | |
| Client Address | `client_address` | `cliente_direccion` | Small Text | Yes* | Client's full address |
| Client Email | `client_email` | `cliente_email` | Data | No | Primary client email |
| Client Email 1 | `client_email_1` | `cliente_email_1` | Data | No | Additional email address |
| Client Email 2 | `client_email_2` | `cliente_email_2` | Data | No | Additional email address |
| **Currency and Exchange** | | - | Section Break | | |
| Currency | `currency` | `moneda` | Select | Yes* | API code: 1=PEN, 2=USD, 3=EUR, 4=GBP |
| Exchange Rate | `exchange_rate` | `tipo_de_cambio` | Float | No | Required if currency = USD |
| | | - | Column Break | | |
| IGV Percentage | `igv_percentage` | `porcentaje_de_igv` | Float | Yes* | Default: 18.00 |
| **Amounts** | | - | Section Break | | |
| Total Taxable | `total_taxable` | `total_gravada` | Currency | No | Total gravada amount |
| Total Unaffected | `total_unaffected` | `total_inafecta` | Currency | No | Total inafecta amount |
| Total Exempt | `total_exempt` | `total_exonerada` | Currency | No | Total exonerada amount |
| Total IGV | `total_igv` | `total_igv` | Currency | Yes* | Total IGV/tax amount |
| | | - | Column Break | | |
| Global Discount | `global_discount` | `descuento_global` | Currency | No | Global discount amount |
| Total Discount | `total_discount` | `total_descuento` | Currency | No | Sum of all discounts |
| Total Advance | `total_advance` | `total_anticipo` | Currency | No | Total advance payment |
| Total Free | `total_free` | `total_gratuita` | Currency | No | Total complimentary amount |
| Total Other Charges | `total_other_charges` | `total_otros_cargos` | Currency | No | Additional charges |
| Total ISC | `total_isc` | `total_isc` | Currency | No | Total ISC amount |
| | | - | Column Break | | |
| Total | `total` | `total` | Currency | Yes* | Final total including taxes |
| **Perception and Retention** | | - | Section Break | | |
| Perception Type | `perception_type` | `percepcion_tipo` | Data | No | SUNAT perception type code |
| Perception Base | `perception_base` | `percepcion_base_imponible` | Currency | No | Taxable base for perception |
| Total Perception | `total_perception` | `total_percepcion` | Currency | No | Perception amount |
| Total with Perception | `total_with_perception` | `total_incluido_percepcion` | Currency | No | Grand total with perception |
| | | - | Column Break | | |
| Withholding Type | `withholding_type` | `retencion_tipo` | Data | No | SUNAT withholding type code |
| Withholding Base | `withholding_base` | `retencion_base_imponible` | Currency | No | Taxable base for withholding |
| Total Retention | `total_retention` | `total_retencion` | Currency | No | Retention amount |
| Total Plastic Bag Tax | `total_plastic_bag_tax` | `total_impuestos_bolsas` | Currency | No | Plastic bag tax (ICBPER) |
| **Detraction** | | - | Section Break | | |
| Subject to Detraction | `subject_to_detraction` | `detraccion` | Check | No | Whether detraction applies |
| Detraction Type | `detraction_type` | `detraccion_tipo` | Select | No | SUNAT detraction type code (001...099) |
| Detraction Total | `detraction_total` | `detraccion_total` | Currency | No | Total detraction amount |
| Detraction Percentage | `detraction_percentage` | `detraccion_porcentaje` | Float | No | Detraction percentage |
| Detraction Payment Method | `detraction_payment_method` | `medio_de_pago_detraccion` | Select | No | Detraction payment method code (001...999) |
| Origin Ubigeo | `origin_ubigeo` | `ubigeo_origen` | Data | No | Origin ubigeo (transport detraction) |
| Origin Address | `origin_address` | `direccion_origen` | Data | No | Origin address |
| Destination Ubigeo | `destination_ubigeo` | `ubigeo_destino` | Data | No | Destination ubigeo |
| Destination Address | `destination_address` | `direccion_destino` | Data | No | Destination address |
| Trip Detail | `trip_detail` | `detalle_viaje` | Data | No | Transport trip detail |
| Transport Reference Value | `transport_reference_value` | `val_ref_serv_trans` | Currency | No | Reference value for transport service |
| Effective Load Reference Value | `effective_load_reference_value` | `val_ref_carga_efec` | Currency | No | Effective load reference value |
| Useful Load Reference Value | `useful_load_reference_value` | `val_ref_carga_util` | Currency | No | Useful load reference value |
| Trip Origin Point | `trip_origin_point` | `punto_origen_viaje` | Data | No | Route origin point (ubigeo) |
| Trip Destination Point | `trip_destination_point` | `punto_destino_viaje` | Data | No | Route destination point (ubigeo) |
| Route Description | `route_description` | `descripcion_tramo` | Data | No | Route segment description |
| Vehicle Configuration | `vehicle_configuration` | `configuracion_vehicular` | Data | No | Vehicle configuration code |
| Vehicle Useful Load Metric Tons | `vehicle_useful_load_metric_tons` | `carga_util_tonel_metricas` | Float | No | Vehicle useful load in tons |
| Vehicle Effective Load Metric Tons | `vehicle_effective_load_metric_tons` | `carga_efec_tonel_metricas` | Float | No | Vehicle effective load in tons |
| Reference Value per Metric Ton | `reference_value_per_metric_ton` | `val_ref_tonel_metrica` | Float | No | Reference value per metric ton |
| Nominal Useful Load Preliminary Reference Value | `nominal_useful_load_preliminary_reference_value` | `val_pre_ref_carga_util_nominal` | Currency | No | Preliminary reference value |
| Empty Return Application Indicator | `empty_return_application_indicator` | `indicador_aplicacion_retorno_vacio` | Check | No | Return-empty factor flag |
| Fishing Vessel Registration | `fishing_vessel_registration` | `matricula_emb_pesquera` | Data | No | Fishing vessel registration |
| Fishing Vessel Name | `fishing_vessel_name` | `nombre_emb_pesquera` | Data | No | Fishing vessel name |
| Sold Species Type Description | `sold_species_type_description` | `descripcion_tipo_especie_vendida` | Data | No | Species type description |
| Unloading Place | `unloading_place` | `lugar_de_descarga` | Data | No | Unloading place |
| Sold Species Quantity | `sold_species_quantity` | `cantidad_especie_vendida` | Float | No | Species quantity |
| Unloading Date | `unloading_date` | `fecha_de_descarga` | Date | No | Unloading date |
| **Credit/Debit Note References** | | - | Section Break | | |
| Base Document Type | `base_document_type` | `documento_que_se_modifica_tipo` | Select | No | Type of document being modified (1-4) |
| Base Document Series | `base_document_series` | `documento_que_se_modifica_serie` | Data | No | Series of document being modified |
| Base Document Number | `base_document_number` | `documento_que_se_modifica_numero` | Int | No | Number of document being modified |
| | | - | Column Break | | |
| Credit Note Reason | `credit_note_reason` | `tipo_de_nota_de_credito` | Select | No | SUNAT credit note reason (1-13) |
| Debit Note Reason | `debit_note_reason` | `tipo_de_nota_de_debito` | Select | No | SUNAT debit note reason (1-5) |
| **Payment and Delivery** | | - | Section Break | | |
| Payment Terms | `payment_terms` | `condiciones_de_pago` | Small Text | No | Payment conditions description |
| Payment Method | `payment_method` | `medio_de_pago` | Data | No | Payment method description |
| Unique Code | `unique_code` | `codigo_unico` | Data | No | External idempotency/control code (`codigo_unico`) |
| Vehicle License Plate | `vehicle_license_plate` | `placa_vehiculo` | Data | No | Delivery vehicle plate |
| Purchase Order | `purchase_order` | `orden_compra_servicio` | Data | No | Client's PO/SO reference |
| **Items** | | - | Section Break | | |
| Items | `items` | `items` | Table | Yes* | Nubefact Invoice Item |
| **Related Guides** | | - | Section Break | | |
| Delivery References | `delivery_references` | `guias` | Table | No | Nubefact Invoice Delivery Reference |
| **Credit Sale** | | - | Section Break | | |
| Credit Sale Installments | `credit_installments` | `venta_al_credito` | Table | No | Nubefact Invoice Payment Installment |
| **Additional Information** | | - | Section Break | | |
| Remarks | `remarks` | `observaciones` | Text | No | Additional notes |
| **More Information** | | - | Tab Break | | |
| **Settings** | | - | Section Break | | |
| Auto Send to SUNAT | `auto_send_to_sunat` | `enviar_automaticamente_a_la_sunat` | Check | No | Send immediately to SUNAT |
| Auto Send to Client | `auto_send_to_client` | `enviar_automaticamente_al_cliente` | Check | No | Email PDF to client |
| PDF Format | `pdf_format` | `formato_de_pdf` | Select | No | Options: "", "A4", "A5", "TICKET" |
| Generated by Contingency | `generated_by_contingency` | `generado_por_contingencia` | Check | No | Contingency issuance flag |
| Goods from Jungle | `goods_from_jungle` | `bienes_region_selva` | Check | No | Goods from jungle region |
| Services from Jungle | `services_from_jungle` | `servicios_region_selva` | Check | No | Services from jungle region |
| Nubecont Sale Type Code | `nubecont_sale_type_code` | `nubecont_tipo_de_venta_codigo` | Data | No | NubeCont sale type code (`nubecont_tipo_de_venta_codigo`) |
| **SUNAT Status** | | - | Section Break | | |
| Status | `status` | - | Select | No | Internal document lifecycle: Draft, Pending Response, Accepted, Voided, Error |
| Accepted by SUNAT | `accepted_by_sunat` | `aceptada_por_sunat` | Check | No | Last known SUNAT acceptance flag |
| Last SUNAT Check | `last_sunat_check` | - | Datetime | No | Last status refresh timestamp |
| SUNAT Response Code | `sunat_response_code` | `sunat_responsecode` | Data | No | SUNAT response code |
| SUNAT Response Message | `sunat_response_message` | `sunat_description` | Text | No | SUNAT response message |
| SUNAT Note | `sunat_note` | `sunat_note` | Text | No | SUNAT note payload |
| SUNAT SOAP Error | `sunat_soap_error` | `sunat_soap_error` | Text | No | SUNAT SOAP transport/app error |
| Error Message | `error_message` | - | Text | No | Internal API/process error |
| | | - | Column Break | | |
| Link URL | `link_url` | `enlace` | Data | No | NubeFact document link |
| CDR URL | `cdr_url` | `enlace_del_cdr` | Data | No | URL to download CDR |
| PDF URL | `pdf_url` | `enlace_del_pdf` | Data | No | URL to download PDF |
| XML URL | `xml_url` | `enlace_del_xml` | Data | No | URL to download XML |
| QR URL | `qr_url` | `cadena_para_codigo_qr` | Data | No | QR content/url returned by NubeFact |
| **Void Information** | | - | Section Break | | |
| Voided | `voided` | `anulado` | Check | No | Whether document is voided |
| Void Date | `void_date` | - | Date | No | Date of void |
| Void Reason | `void_reason` | `motivo` | Small Text | No | Reason for voiding |
| | | - | Column Break | | |
| Void Status | `void_status` | - | Select | No | Options: Pending, Accepted, Rejected |
| Void Ticket | `void_ticket` | `sunat_ticket_numero` | Data | No | SUNAT void ticket number |

## Child Table: Nubefact Invoice Item

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| UOM | `uom` | `unidad_de_medida` | Data | Yes* | API UOM code (e.g., NIU, ZZ) |
| Item Code | `item_code` | `codigo` | Data | Yes* | Internal product/service code |
| SUNAT Product Code | `sunat_product_code` | `codigo_producto_sunat` | Data | No | 8-digit SUNAT catalog code |
| Description | `description` | `descripcion` | Text | Yes* | Product/service description |
| Quantity | `quantity` | `cantidad` | Float | Yes* | Item quantity |
| Unit Price | `unit_price` | `valor_unitario` | Currency | Yes* | Unit price without taxes |
| Unit Price with Tax | `unit_price_with_tax` | `precio_unitario` | Currency | Yes* | Unit price including taxes |
| Discount | `discount` | `descuento` | Currency | No | Discount per item |
| Line Total | `line_total` | `subtotal` | Currency | Yes* | Line subtotal without taxes |
| IGV Type | `igv_type` | `tipo_de_igv` | Select | Yes* | Includes 1-17 and 20 per NubeFact catalog |
| IVAP Type | `ivap_type` | `tipo_de_ivap` | Select | No | 17=IVAP gravado, 101=IVAP gratuito |
| IGV | `igv` | `igv` | Currency | Yes* | IGV amount for this line |
| Plastic Bag Tax | `plastic_bag_tax` | `impuesto_bolsas` | Currency | No | ICBPER amount for the line |
| Line Total with Tax | `line_total_with_tax` | `total` | Currency | Yes* | Line total including taxes |
| Downpayment Regularization | `downpayment_regularization` | `anticipo_regularizacion` | Check | No | Is downpayment regularization |
| Downpayment Document Series | `downpayment_document_series` | `anticipo_documento_serie` | Data | No | Downpayment document series |
| Downpayment Document Number | `downpayment_document_number` | `anticipo_documento_numero` | Data | No | Downpayment document number |
| ISC Type | `isc_type` | `tipo_de_isc` | Select | No | ISC type code (1, 2, 3) |
| ISC | `isc` | `isc` | Currency | No | ISC amount for the line |

## Child Table: Nubefact Invoice Delivery Reference

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| Guide Type | `guide_type` | `guia_tipo` | Select | Yes* | 1=Guía remitente, 2=Guía transportista |
| Guide Series and Number | `guide_series_number` | `guia_serie_numero` | Data | Yes* | Format: "0001-23" |

## Child Table: Nubefact Invoice Payment Installment

| Field Label | Field Name | NubeFact Field | Field Type | Required | Description |
|------------|------------|----------------|------------|----------|-------------|
| Installment Number | `installment_number` | `cuota` | Int | Yes* | Installment sequence |
| Payment Date | `payment_date` | `fecha_de_pago` | Date | Yes* | Due date for installment |
| Amount | `amount` | `importe` | Currency | Yes* | Installment amount |

\* `Required = Yes*` means canonical/API-required at runtime payload validation level (not necessarily marked mandatory in DocType schema yet).

## Settings
- Auto Name: `format:{series}-{number}`
- Sort Field: `issue_date`
- Sort Order: DESC

## Permissions
- Accounts Manager: Full access (create, read, write, submit, cancel)
- Accounts User: Create, Read, Write, Submit
- Sales User: Read only

## Implementation Status
- ✅ Schema implemented in DocType JSON files.
- 🚧 Runtime API methods (`send_to_nubefact`, `refresh_sunat_status`, `void_in_nubefact`) remain application-level implementation work.
