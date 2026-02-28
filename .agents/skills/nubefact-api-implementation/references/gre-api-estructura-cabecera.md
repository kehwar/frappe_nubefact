# GRE API — ESTRUCTURA PARA GENERAR GUÍA DE REMISIÓN REMITENTE

> Source: `assets/gre-manual-google-doc.md` — ESTRUCTURA PARA GENERAR GUÍA DE REMISIÓN REMITENTE

## CABECERA DEL DOCUMENTO

| CABECERA DEL DOCUMENTO |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| operación | Este valor siempre deberá ser "generar\_guia" exactamente. | String | Obligatorio | 11 exactos |
| tipo\_de\_comprobante | Tipo de COMPROBANTE que desea generar: 7 \= GUÍA REMISIÓN REMITENTE 8 \= GUÍA REMISIÓN TRANSPORTISTA | Integer | Obligatorio | 1 exacto |
| serie | Para GRE Remitente: debe empezar con "T" (Ejm: TTT1) Para GRE Transportista: debe empezar con "V" (Ejm: VVV1) | String | Obligatorio | 4 exactos |
| número | Número correlativo del documento, sin ceros a la izquierda | Integer | Obligatorio | 1 hasta 8 |
| cliente\_tipo\_de\_documento | 6 \= RUC \- REGISTRO ÚNICO DE CONTRIBUYENTE 1 \= DNI \- DOC. NACIONAL DE IDENTIDAD 4 \= CARNET DE EXTRANJERÍA 7 \= PASAPORTE A \= CÉDULA DIPLOMÁTICA DE IDENTIDAD 0 \= NO DOMICILIADO, SIN RUC (EXPORTACIÓN) Para GRE Remitente: este campo se refiere al Destinatario. Para GRE Transportista: este campo se refiere al Remitente. | Integer | Obligatorio | 1 exacto |
| cliente\_numero\_de\_documento | Ejemplo: RUC del CLIENTE, número de DNI, Etc. | String | Obligatorio | 1 hasta 15 |
| cliente\_denominacion | Razón o nombre completo del CLIENTE. | String | Obligatorio | 1 hasta 100 |
| cliente\_direccion | Dirección completa. | String | Obligatorio | 1 hasta 100 |
| cliente\_email | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente\_email\_1 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente\_email\_2 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| fecha\_de\_emision | Debe ser la fecha actual. Formato DD-MM-AAAA**Importante:** **Como máximo puede emitir con 1 día anterior a la fecha actual.** Ejemplo: 10-05-2017 | Date | Obligatorio | 10 exactos |
| observaciones | Texto de 0 hasta 1000 caracteres. Si se desea saltos de línea para la representación impresa o PDF usar \<br\>.  Ejemplo: XXXXX \<br\> YYYYYY | Text | Opcional | Hasta 5 |
| motivo\_de\_traslado | Solo para GRE REMITENTE: "01" \= "VENTA" "14" \= "VENTA SUJETA A CONFIRMACION DEL COMPRADOR" "02" \= "COMPRA" "04" \= "TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA" "18" \= "TRASLADO EMISOR ITINERANTE CP" "08" \= "IMPORTACION" "09" \= "EXPORTACION" "13" \= "OTROS" "05" \= "CONSIGNACION" "17" \= "TRASLADO DE BIENES PARA TRANSFORMACION""03" \= "VENTA CON ENTREGA A TERCEROS" "06" \= "DEVOLUCION" "07" \= "RECOJO DE BIENES TRANSFORMADOS" | String | Obligatorio | 2 exactos |
| motivo\_de\_traslado\_otros\_descripcion | Solo se aplica para Motivo de traslado: "13" \- OTROS Descripción adicional alfanumérico con espaciados simples. | String | Opcional | Hasta 70 caracteres. |
| documento\_relacionado\_codigo  | **Solo para motivo de traslado importación ó exportación)** 50 \= "Declaración Aduanera de Mercancías"52 \= "Declaración Simplificada (DS)" **CÓDIGO DAM o DS** \* Enviar primero la SERIE del código DAM o DS hasta 4 dígitos numéricos. \* Posteriormente enviar el código DAM o DS.  **IMPORTANTE:** Si el motivo de traslado es IMPORTACIÓN debe registrar el siguiente formato en el formulario del código DAM o DS. **a)** Si el tipo de documento relacionado es 50 \- Declaración Aduanera de Mercancías el formato sería: xxxx(serie)/xxx-xxxx-10-xxxxxx(DAM) Ejemplo: 1/123-1234-10-123456 **b)** Si el tipo de documento relacionado es 52 \- Declaración Simplificada (DS) el formato sería: xxxx(serie)/xxx-xxxx-18-xxxxxx(DS) Ejemplo: 1/123-1234-18-123456 \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Si el motivo de traslado es EXPORTACIÓN debe registrar el siguiente formato en el formulario del código DAM o DS. **a)** Si el tipo de documento relacionado es 50 \- Declaración Aduanera de Mercancías el formato sería: xxxx(serie)/xxx-xxxx-40-xxxxxx(DAM) Ejemplo: 1/123-1234-40-123456 **b)** Si el tipo de documento relacionado es 52 \- Declaración Simplificada (DS) el formato sería: xxxx(serie)/xxx-xxxx-48-xxxxxx(DS) Ejemplo: 1/123-1234-48-123456  | String | Condicional | 2 exactos |
| peso\_bruto\_total | En KILOGRAMOS, ejemplo: 4.00 Importante: debe ser mayor a "0". | Decimal | Obligatorio | 1 hasta  12 enteros, hasta con  10 decimales |
| peso\_bruto\_unidad\_de\_medida  | Código de la unidad de medida, solo se aceptan: KGM \= "Kilogramos"óTNE \= "Toneladas" | String | Obligatorio | 3 dígitos. |
| numero\_de\_bultos | Sólo para GRE Remitente Cantidad de bultos. Importante: debe ser numérico (entero) | Decimal | Obligatorio | 1 hasta  6 enteros |
| tipo\_de\_transporte | Sólo para GRE Remitente "01" \= "TRANSPORTE PÚBLICO" "02" \= "TRANSPORTE PRIVADO" | String | Obligatorio | 2 exactos |
| fecha\_de\_inicio\_de\_traslado | Para GRE Remitente y Transportista Fecha de inicio del traslado. Formato DD-MM-AAAA Ejemplo: 10-05-2017 | Date | Obligatorio | 10 exactos |
| transportista\_documento\_tipo | Sólo para GRE Remitente 6 \= RUC \- REGISTRO ÚNICO DE CONTRIBUYENTE Sólo cuando 'tipo\_de\_transporte' es "01" | Integer | Condicional | 1 exacto |
| transportista\_documento\_numero | Sólo para GRE Remitente Ejemplo: RUC del CLIENTE Sólo cuando 'tipo\_de\_transporte' es "01" | String | Condicional | 11 exacto |
| transportista\_denominacion | Sólo para GRE Remitente Razón o nombre completo del TRANSPORTISTA. Sólo cuando 'tipo\_de\_transporte' es "01" | String | Condicional | 1 hasta 100 |
| transportista\_placa\_numero | Para GRE Remitente y Transportista Ejemplo: ABC321 (no deben ser ceros ni debe tener guiones) | String | Obligatorio | 6 hasta 8 |
| tuc\_vehiculo\_principal | Para GRE TransportistaTarjeta Única de Circulación Electrónica o Certificado de Habilitación vehicular Ejemplo: ABC321981R (Solo se permite mayúsculas y números alfanumérico sin guiones o cualquier otro caracter) | String | Opcional | 10 hasta 15 dígitos. |
| conductor\_documento\_tipo | 1 \= DNI \- DOC. NACIONAL DE IDENTIDAD 4 \= CARNET DE EXTRANJERÍA 7 \= PASAPORTE A \= CÉDULA DIPLOMÁTICA DE IDENTIDAD 0 \= NO DOMICILIADO, SIN RUC (EXPORTACIÓN) Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | Integer | Condicional | 1 exacto |
| conductor\_documento\_numero | Ejemplo: Número de DNI, Etc. Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | String | Condicional | 1 hasta 15 |
| conductor\_denominacion | Razón o nombre completo del CONDUCTOR. Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | String | Condicional | 1 hasta 100 |
| conductor\_nombre | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | String | Condicional | Hasta 250 |
| conductor\_apellidos | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | String | Condicional | Hasta 250 |
| conductor\_numero\_licencia | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". Para GRE Transportista: dato obligatorio. | String | Condicional | 9 hasta 10 |
| destinatario\_documento\_tipo | A quién va dirigido el envío Sólo para GRE Transportista 6 \= RUC \- REGISTRO ÚNICO DE CONTRIBUYENTE 1 \= DNI \- DOC. NACIONAL DE IDENTIDAD 4 \= CARNET DE EXTRANJERÍA 7 \= PASAPORTE A \= CÉDULA DIPLOMÁTICA DE IDENTIDAD 0 \= NO DOMICILIADO, SIN RUC (EXPORTACIÓN) | String | Condicional | 1 exacto |
| destinatario\_documento\_numero | Sólo para GRE Transportista | String | Condicional | 1 hasta 15 |
| destinatario\_denominacion | Sólo para GRE Transportista | String | Condicional | 1 hasta 100 |
| mtc | Solo se permite Alfanumérico Mayúsculas. | String | Opcional | Hasta 20  |
| sunat\_envio\_indicador | **GRE Transportista** 01 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Remitente 02 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Subcontratador 03 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Tercero 04 \= SUNAT\_Envio\_IndicadorRetornoVehiculoEnvaseVacio 05 \= SUNAT\_Envio\_IndicadorRetornoVehiculoVacio **GRE Remitente** 04 \= SUNAT\_Envio\_IndicadorRetornoVehiculoEnvaseVacio 05 \= SUNAT\_Envio\_IndicadorRetornoVehiculoVacio 06 \= SUNAT\_Envio\_IndicadorTrasladoVehiculoM1L  | String | Opcional | 2 exactos |
| subcontratador\_documento\_tipo | Solo se aplica si **"sunat\_envio\_indicador"** es 02 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Subcontratador Solo se acepta el tipo de documento **6 \=  RUC** | Integer | Condicional | 1 exacto |
| subcontratador\_documento\_numero | Solo se aplica si **"sunat\_envio\_indicador"** es 02 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Subcontratador | String | Condicional | 11 caracteres exactos |
| subcontratador\_denominacion | Solo se aplica si **"sunat\_envio\_indicador"** es 02 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Subcontratador | String | Condicional | hasta 250 |
| pagador\_servicio\_documento\_tipo\_identidad | Solo se aplica si **"sunat\_envio\_indicador"** es 03 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Tercero 6 \= RUC \- REGISTRO ÚNICO DE CONTRIBUYENTE 1 \= DNI \- DOC. NACIONAL DE IDENTIDAD 4 \= CARNET DE EXTRANJERÍA 7 \= PASAPORTE A \= CÉDULA DIPLOMÁTICA DE IDENTIDAD 0 \= NO DOMICILIADO, SIN RUC (EXPORTACIÓN)  | String | Condicional | 1 exacto |
| pagador\_servicio\_documento\_numero\_identidad | Solo se aplica si **"sunat\_envio\_indicador"** es 03 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Tercero | String | Condicional | Hasta 15  |
| pagador\_servicio\_denominacion | Solo se aplica si **"sunat\_envio\_indicador"** es 03 \= SUNAT\_Envio\_IndicadorPagadorFlete\_Tercero | String | Condicional | Hasta 250 |
| punto\_de\_partida\_ubigeo | Usar la siguiente tabla según corresponda: [https://drive.google.com/open?id=1-aHRVG5c5-IUkTC\_jOJ4ktna6MCR86rK8Bc7AwW2whA](https://drive.google.com/open?id=1-aHRVG5c5-IUkTC_jOJ4ktna6MCR86rK8Bc7AwW2whA) | String | Obligatorio | Hasta 6 |
| punto\_de\_partida\_direccion | Dirección exacta | String | Obligatorio | Hasta 150 |
| punto\_de\_partida\_codigo\_establecimiento\_sunat | Para los motivos de traslado con código 04, 18Ejemplo: "0000" | String | Condicional | 4 exactos |
| punto\_de\_llegada\_ubigeo | Usar la siguiente tabla según corresponda: [https://drive.google.com/open?id=1-aHRVG5c5-IUkTC\_jOJ4ktna6MCR86rK8Bc7AwW2whA](https://drive.google.com/open?id=1-aHRVG5c5-IUkTC_jOJ4ktna6MCR86rK8Bc7AwW2whA) | String | Obligatorio | Hasta 6 |
| punto\_de\_llegada\_direccion | Dirección exacta | String | Obligatorio | Hasta 150 |
| punto\_de\_llegada\_codigo\_establecimiento\_sunat | Para los motivos de traslado con código 04, 18Ejemplo: "0000" | String | Condicional | 4 exactos |
| enviar\_automaticamente\_al\_cliente | false \= FALSO (En minúsculas) true \= VERDADERO (En minúsculas) Se envía sólo si la GRE fue aceptada por la Sunat. | Boolean | Condicional | Hasta 5 |
| formato\_de\_pdf | Formato de PDF que se desea generar para la representación, si se deja en blanco se genera el formato definido por defecto en NUBEFACT. Se puede elegir entre A4 o TICKET. | String | Opcional | 2 hasta 5 |
| items | Permite items anidados, se refiere a los ITEMS o LÍNEAS del comprobante, el detalle en un cuadro más abajo. | \- | \- | \- |
| documento\_relacionado | Permite documentos anidados, se refiere a los Documentos que van relacionados a una Guia, el detalle en un cuadro más abajo | \- | \- | \- |
