# DocType Schema: Nubefact Guía de Remisión

## Scope

- Main DocType only (`Nubefact Guía de Remisión`).
- Child tables were split into dedicated files:
	- `doctype-nubefact-guia-remision-item-schema.md`
	- `doctype-nubefact-guia-remision-documento-relacionado-schema.md`
	- `doctype-nubefact-guia-remision-vehiculo-secundario-schema.md`
	- `doctype-nubefact-guia-remision-conductor-secundario-schema.md`

## Source References

- `gre-api-estructura-cabecera.md`
- `gre-api-estructura-respuesta.md`

## Payload Fields (same naming as GRE reference)

| Atributo | Tipo de dato | Requisito | Longitud |
|---|---|---|---|
| operación | String | Obligatorio | 11 exactos |
| tipo_de_comprobante | Integer | Obligatorio | 1 exacto |
| serie | String | Obligatorio | 4 exactos |
| número | Integer | Obligatorio | 1 hasta 8 |
| cliente_tipo_de_documento | Integer | Obligatorio | 1 exacto |
| cliente_numero_de_documento | String | Obligatorio | 1 hasta 15 |
| cliente_denominacion | String | Obligatorio | 1 hasta 100 |
| cliente_direccion | String | Obligatorio | 1 hasta 100 |
| cliente_email | String | Opcional | 1 hasta 250 |
| cliente_email_1 | String | Opcional | 1 hasta 250 |
| cliente_email_2 | String | Opcional | 1 hasta 250 |
| fecha_de_emision | Date | Obligatorio | 10 exactos |
| observaciones | Text | Opcional | Hasta 5 |
| motivo_de_traslado | String | Obligatorio | 2 exactos |
| motivo_de_traslado_otros_descripcion | String | Opcional | Hasta 70 caracteres |
| documento_relacionado_codigo | String | Condicional | 2 exactos |
| peso_bruto_total | Decimal | Obligatorio | 1 hasta 12 enteros, hasta con 10 decimales |
| peso_bruto_unidad_de_medida | String | Obligatorio | 3 dígitos |
| numero_de_bultos | Decimal | Obligatorio | 1 hasta 6 enteros |
| tipo_de_transporte | String | Obligatorio | 2 exactos |
| fecha_de_inicio_de_traslado | Date | Obligatorio | 10 exactos |
| transportista_documento_tipo | Integer | Condicional | 1 exacto |
| transportista_documento_numero | String | Condicional | 11 exacto |
| transportista_denominacion | String | Condicional | 1 hasta 100 |
| transportista_placa_numero | String | Obligatorio | 6 hasta 8 |
| tuc_vehiculo_principal | String | Opcional | 10 hasta 15 dígitos |
| conductor_documento_tipo | Integer | Condicional | 1 exacto |
| conductor_documento_numero | String | Condicional | 1 hasta 15 |
| conductor_denominacion | String | Condicional | 1 hasta 100 |
| conductor_nombre | String | Condicional | Hasta 250 |
| conductor_apellidos | String | Condicional | Hasta 250 |
| conductor_numero_licencia | String | Condicional | 9 hasta 10 |
| destinatario_documento_tipo | String | Condicional | 1 exacto |
| destinatario_documento_numero | String | Condicional | 1 hasta 15 |
| destinatario_denominacion | String | Condicional | 1 hasta 100 |
| mtc | String | Opcional | Hasta 20 |
| sunat_envio_indicador | String | Opcional | 2 exactos |
| subcontratador_documento_tipo | Integer | Condicional | 1 exacto |
| subcontratador_documento_numero | String | Condicional | 11 caracteres exactos |
| subcontratador_denominacion | String | Condicional | hasta 250 |
| pagador_servicio_documento_tipo_identidad | String | Condicional | 1 exacto |
| pagador_servicio_documento_numero_identidad | String | Condicional | Hasta 15 |
| pagador_servicio_denominacion | String | Condicional | Hasta 250 |
| punto_de_partida_ubigeo | String | Obligatorio | Hasta 6 |
| punto_de_partida_direccion | String | Obligatorio | Hasta 150 |
| punto_de_partida_codigo_establecimiento_sunat | String | Condicional | 4 exactos |
| punto_de_llegada_ubigeo | String | Obligatorio | Hasta 6 |
| punto_de_llegada_direccion | String | Obligatorio | Hasta 150 |
| punto_de_llegada_codigo_establecimiento_sunat | String | Condicional | 4 exactos |
| enviar_automaticamente_al_cliente | Boolean | Condicional | Hasta 5 |
| formato_de_pdf | String | Opcional | 2 hasta 5 |
| items | - | - | - |
| documento_relacionado | - | - | - |

## Response Fields (same naming as GRE reference)

| Atributo | Tipo de dato |
|---|---|
| tipo_de_comprobante | Integer |
| serie | String |
| numero | Integer |
| enlace | String |
| aceptada_por_sunat | Boolean |
| sunat_description | String |
| sunat_note | String |
| sunat_responsecode | String |
| sunat_soap_error | String |
| pdf_zip_base64 | Text |
| xml_zip_base64 | Text |
| cdr_zip_base64 | Text |
| cadena_para_codigo_qr | Text |
| enlace_del_pdf | Text |
| enlace_del_xml | Text |
| enlace_del_cdr | Text |

## Extra Fields (not present in NubeFact payload/response) — English only

These fields stay in English because they are internal DocType/system fields and are not part of the NubeFact API schema:

- `status`
- `title`
- `branch`
- `skip_required_fields_validation`
- `last_sunat_check`
- `error_message`

