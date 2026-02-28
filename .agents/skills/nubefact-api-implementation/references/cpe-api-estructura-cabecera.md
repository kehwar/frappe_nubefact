# CPE API — ESTRUCTURA PARA GENERAR FACTURAS, BOLETAS Y NOTAS

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA PARA GENERAR FACTURAS, BOLETAS Y NOTAS (CABECERA DEL DOCUMENTO)

## Sección 1 — Identificación del comprobante

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| operación | Este valor siempre deberá ser "generar_comprobante" para enviar FACTURAS, BOLETAS, NOTAS DE CRÉDITO o DÉBITO | String | Obligatorio | 11 exactos |
| tipo_de_comprobante | Tipo de COMPROBANTE que desea generar: 1 = FACTURA 2 = BOLETA 3 = NOTA DE CRÉDITO 4 = NOTA DE DÉBITO | Integer | Obligatorio | 1 exacto |
| serie | Empieza con "F" para FACTURAS y NOTAS ASOCIADAS. Empieza con "B" para BOLETAS DE VENTA y NOTAS ASOCIADAS Si está comunicando un comprobante emitido en contingencia, la serie debe empezar NO debe empezar con "F" ni con "B". Debería empezar con "0", ejemplo: "0001" | String | Obligatorio | 4 exactos |
| número | Número correlativo del documento, sin ceros a la izquierda | Integer | Obligatorio | 1 hasta 8 |
| sunat_transaction | La mayoría de veces se usa el 1, las demás son para tipos de operaciones muy especiales, no dudes en consultar con nosotros para más información: 1 = VENTA INTERNA 2 = EXPORTACIÓN 4 = VENTA INTERNA – ANTICIPOS 29 = VENTAS NO DOMICILIADOS QUE NO CALIFICAN COMO EXPORTACIÓN. 30 = OPERACIÓN SUJETA A DETRACCIÓN. 33 = DETRACCIÓN - SERVICIOS DE TRANSPORTE CARGA 34 = OPERACIÓN SUJETA A PERCEPCIÓN 32 = DETRACCIÓN - SERVICIOS DE TRANSPORTE DE PASAJEROS. 31 = DETRACCIÓN - RECURSOS HIDROBIOLÓGICOS 35 = VENTA NACIONAL A TURISTAS - TAX FREE | Integer | Obligatorio | 1 hasta 2 |

## Sección 2 — Datos del cliente

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| cliente_tipo_de_documento | 6 = RUC - REGISTRO ÚNICO DE CONTRIBUYENTE 1 = DNI - DOC. NACIONAL DE IDENTIDAD - = VARIOS - VENTAS MENORES A S/.700.00 Y OTROS 4 = CARNET DE EXTRANJERÍA 7 = PASAPORTE A = CÉDULA DIPLOMÁTICA DE IDENTIDAD B = DOC.IDENT.PAIS.RESIDENCIA-NO.D 0 = NO DOMICILIADO, SIN RUC (EXPORTACIÓN) G = Salvoconducto | String | Obligatorio | 1 exacto |
| cliente_numero_de_documento | Ejemplo: RUC del CLIENTE, número de DNI, Etc. | String | Obligatorio | 1 hasta 15 |
| cliente_denominacion | Razón o nombre completo del CLIENTE. | String | Obligatorio | 1 hasta 100 |
| cliente_direccion | Dirección completa (OPCIONAL en caso de ser una BOLETA DE VENTA o NOTA ASOCIADA). | String | Obligatorio | 1 hasta 100 |
| cliente_email | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente_email_1 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente_email_2 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |

## Sección 3 — Fechas y moneda

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| fecha_de_emision | Debe ser la fecha actual. Formato DD-MM-AAAA Ejemplo: 10-05-2017 | Date | Obligatorio | 10 exactos |
| fecha_de_vencimiento | Deber ser fecha posterior a la fecha de emisión | Date | Opcional | 10 exactos |
| moneda | De necesitar más monedas no dude en contactarse con nosotros. 1 = SOLES 2 = DÓLARES 3 = EUROS 4 = LIBRA ESTERLINA | Integer | Obligatorio | 1 exacto |
| tipo_de_cambio | Ejemplo: 3.421 | Numeric | Condicional | 1 entero con 3 decimales |

## Sección 4 — Totales e impuestos globales

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| porcentaje_de_igv | Ejemplo: 18.00 | Numeric | Obligatorio | 1 hasta 2 enteros con 2 decimales |
| descuento_global | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_descuento | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_anticipo | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_gravada | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_inafecta | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_exonerada | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_igv | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_gratuita | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_otros_cargos | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_isc |  | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_impuestos_bolsas | Ejemplo: 0.10 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total | Ejemplo: 1305.05 | Numeric | Obligatorio | 1 hasta 12 enteros con 2 decimales |

## Sección 5 — Percepción y retención

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| percepcion_tipo | 1 = PERCEPCIÓN VENTA INTERNA - TASA 2% 2 = PERCEPCIÓN ADQUISICIÓN DE COMBUSTIBLE-TASA 1% 3 = PERCEPCIÓN REALIZADA AL AGENTE DE PERCEPCIÓN CON TASA ESPECIAL - TASA 0.5% | Integer | Condicional | 1 exacto |
| percepcion_base_imponible | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_percepcion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_incluido_percepcion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| retencion_tipo | 1 = TASA 3% 2 = TASA 6% | Integer | Condicional | 1 exacto |
| retencion_base_imponible | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total_retencion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |

## Sección 6 — Notas (documento relacionado)

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| documento_que_se_modifica_tipo | 1 = FACTURAS ELECTRÓNICAS 2 = BOLETAS DE VENTA ELECTRÓNICAS | Integer | Condicional | 1 exacto |
| documento_que_se_modifica_serie | SERIE de la FACTURA o BOLETA que se modifica (previamente comunicado) | String | Condicional | 4 exactos |
| documento_que_se_modifica_numero | NÚMERO de la FACTURA o BOLETA que se modifica (previamente comunicado) | Integer | Condicional | 1 hasta 8 |
| tipo_de_nota_de_credito | 1 = ANULACIÓN DE LA OPERACIÓN 2 = ANULACIÓN POR ERROR EN EL RUC 3 = CORRECCIÓN POR ERROR EN LA DESCRIPCIÓN 4 = DESCUENTO GLOBAL 5 = DESCUENTO POR ÍTEM 6 = DEVOLUCIÓN TOTAL 7 = DEVOLUCIÓN POR ÍTEM 8 = BONIFICACIÓN 9 = DISMINUCIÓN EN EL VALOR 10= OTROS CONCEPTOS 11= AJUSTES AFECTOS AL IVAP 12 = AJUSTES DE OPERACIONES DE EXPORTACIÓN 13 = AJUSTES - MONTOS Y/O FECHAS DE PAGO | Integer | Condicional | 1 hasta 2 |
| tipo_de_nota_de_debito | 1 = INTERESES POR MORA 2 = AUMENTO DE VALOR 3 = PENALIDADES 4= AJUSTES AFECTOS AL IVAP 5 = AJUSTES DE OPERACIONES DE EXPORTACIÓN | Integer | Condicional | 1 exacto |

## Sección 8 — Detracción (general)

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| detraccion | false = FALSO (En minúsculas) true = VERDADERO (En minúsculas) | Boolean | Condicional | Hasta 5 |
| detraccion_tipo | 1 = 001 Azúcar y melaza de caña 2 = 002 Arroz 3 = 003 Alcohol etílico 4 = 004 Recursos Hidrobiológicos 5 = 005 Maíz amarillo duro 7 = 007 Caña de azúcar 8 = 008 Madera 9 = 009 Arena y piedra. 10 = 010 Residuos, subproductos, desechos, recortes y desperdicios 11 = 011 Bienes gravados con el IGV, o renuncia a la exoneración 12 = 012 Intermediación laboral y tercerización 13 = 014 Carnes y despojos comestibles 14 = 016 Aceite de pescado 15 = 017 Harina, polvo y pellets de pescado, crustáceos, moluscos y demás invertebrados acuáticos 17 = 019 Arrendamiento de bienes muebles 18 = 020 Mantenimiento y reparación de bienes muebles 19 = 021 Movimiento de carga 20 = 022 Otros servicios empresariales 21 = 023 Leche 22 = 024 Comisión mercantil 23 = 025 Fabricación de bienes por encargo 24 = 026 Servicio de transporte de personas 25 = 027 Servicio de transporte de carga 26 = 028 Transporte de pasajeros 28 = 030 Contratos de construcción 29 = 031 Oro gravado con el IGV 30 = 032 Paprika y otros frutos de los géneros capsicum o pimienta 32 = 034 Minerales metálicos no auríferos 33 = 035 Bienes exonerados del IGV 34 = 036 Oro y demás minerales metálicos exonerados del IGV 35 = 037 Demás servicios gravados con el IGV 37 = 039 Minerales no metálicos 38 = 040 Bien inmueble gravado con IGV 39 = 041 Plomo 40 = 013 ANIMALES VIVOS 41 = 015 ABONOS, CUEROS Y PIELES DE ORIGEN ANIMAL 42 = 099 LEY 30737 43 = 044 Servicio de beneficio de minerales metálicos gravado con el IGV 44 = 045 Minerales de oro y sus concentrados gravados con el IGV | Integer | Condicional | 1 hasta 2 |
| detraccion_total | Total de la Detracción | Numeric | Condicional | 1 hasta 12 enteros, hasta con 10 decimales |
| detraccion_porcentaje | Porcentaje - Detracción | Numeric | Condicional | 1 hasta 3 enteros, hasta con 5 decimales |
| medio_de_pago_detraccion | 1 = 001 - Depósito en cuenta 2 = 002 - Giro 3 = 003 - Transferencia de fondos 4 = 004 - Orden de pago 5 = 005 - Tarjeta de débito 6 = 006 - Tarjeta de crédito emitida en el país por una empresa del sistema financiero 7 = 007 - Cheques con la cláusula de NO NEGOCIABLE, INTRANSFERIBLES, NO A LA ORDEN u otra equivalente, a que se refiere el inciso g) del artículo 5 de la ley 8 = 008 - Efectivo, por operaciones en las que no existe obligación de utilizar medio de pago 9 = 009 - Efectivo, en los demás casos 10 = 010 - Medios de pago usados en comercio exterior 11 = 011 - Documentos emitidos por las EDPYMES y las cooperativas de ahorro y crédito no autorizadas a captar depósitos del público 12 = 012 - Tarjeta de crédito emitida en el país o en el exterior por una empresa no perteneciente al sistema financiero, cuyo objeto principal sea la emisión y administración de tarjetas de crédito 13 = 013 - Tarjetas de crédito emitidas en el exterior por empresas bancarias o financieras no domiciliadas 14 = 101 - Transferencias – Comercio exterior 15 = 102 - Cheques bancarios - Comercio exterior 16 = 103 - Orden de pago simple - Comercio exterior 17 = 104 - Orden de pago documentario - Comercio exterior 18 = 105 - Remesa simple - Comercio exterior 19 = 106 - Remesa documentaria - Comercio exterior 20 = 107 - Carta de crédito simple - Comercio exterior 21 = 108 - Carta de crédito documentario - Comercio exterior 22 = 999 - Otros medios de pago. Nota: recuerde tener registrado el número de cuenta para detracciones en la opción de cuentas bancarias en su panel. | Numeric | Condicional | 1 hasta 2 |

## Sección 9 — Detracción (transporte de carga)

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| ubigeo_origen | Código de Ubigeo de Origen: http://www.sunat.gob.pe/legislacion/superin/2018/anexoI-254-2018.pdf | Integer | Condicional | 6 exactos |
| direccion_origen | Dirección completa del origen (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA) | String | Condicional | 1 hasta 100 |
| ubigeo_destino | Código de Ubigeo de Destino: http://www.sunat.gob.pe/legislacion/superin/2018/anexoI-254-2018.pdf | Integer | Condicional | 6 exactos |
| direccion_destino | Dirección completa del destino (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA) | String | Condicional | 1 hasta 100 |
| detalle_viaje | Detalle del transporte. | String | Condicional | 1 hasta 100 |
| val_ref_serv_trans | Valor Referencia del servicio de Transporte (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val_ref_carga_efec | Valor Referencial Carga Efectiva (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val_ref_carga_util | Valor Referencial Carga Útil (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| punto_origen_viaje | Punto de origen del viaje (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional): http://www.sunat.gob.pe/legislacion/superin/2018/anexoI-254-2018.pdf | Integer | Condicional | 6 exactos |
| punto_destino_viaje | Punto de destino del viaje (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional): http://www.sunat.gob.pe/legislacion/superin/2018/anexoI-254-2018.pdf | Integer | Condicional | 6 exactos |
| descripcion_tramo | Descripción del tramo (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | String | Condicional | 1 hasta 100 |
| val_ref_carga_efec_tramo_virtual | Valor preliminar referencial sobre la carga efectiva (por el tramo virtual recorrido) (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| configuracion_vehicular | Configuración vehicular del vehículo (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | String | Condicional | Hasta 15 |
| carga_util_tonel_metricas | Carga útil en toneladas métricas del vehículo (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| carga_efec_tonel_metricas | Carga efectiva en toneladas métricas del vehículo (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val_ref_tonel_metrica | Valor referencial por tonelada métrica (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Numeric | Condicional | 1 hasta 5 |
| val_pre_ref_carga_util_nominal | Valor preliminar referencial por carga útil nominal (tratándose de más de 1 vehículo) (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| indicador_aplicacion_retorno_vacio | Indicador de aplicación de factor de retorno al vacío (SOLO EN TIPO DETRACCIÓN DE TRANSPORTE DE CARGA - Opcional) | Boolean | Condicional | Hasta 5 |

## Sección 10 — Detracción (recursos hidrobiológicos)

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| matricula_emb_pesquera | Matrícula de la embarcación pesquera (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS) | String | Condicional | Hasta 15 |
| nombre_emb_pesquera | Nombre de la embarcación pesquera (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS) | String | Condicional | Hasta 50 |
| descripcion_tipo_especie_vendida | Descripción del tipo de la especie vendida (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS) | String | Condicional | Hasta 100 |
| lugar_de_descarga | Lugar de descarga (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS) | String | Condicional | Hasta 200 |
| cantidad_especie_vendida | Cantidad de la especie vendida (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS) | Numeric | Condicional | 12 enteros, hasta con 2 decimales |
| fecha_de_descarga | Fecha de descarga (SOLO EN TIPO DETRACCIÓN DE RECURSOS HIDROBIOLÓGICOS). Formato AAAA-MM-DD. Ejemplo: 2020-05-22 | Date | Condicional | 10 exactos |

## Sección 11 — Otras características del comprobante

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| enviar_automaticamente_a_la_sunat | false = FALSO (En minúsculas) true = VERDADERO (En minúsculas) | Boolean | Condicional | Hasta 5 |
| enviar_automaticamente_al_cliente | false = FALSO (En minúsculas) true = VERDADERO (En minúsculas) | Boolean | Condicional | Hasta 5 |
| codigo_unico | Usarlo sólo si deseas que controlemos la generación de documentos. Código único generado y asignado por tu sistema. Por ejemplo puede estar compuesto por el tipo de documento, serie y número correlativo. | String | Opcional | 1 hasta 20 |
| formato_de_pdf | Formato de PDF que se desea generar para la representación, si se deja en blanco se genera el formato definido por defecto en NUBEFACT. Se puede elegir entre A4, A5 o TICKET. | String | Opcional | 2 hasta 5 |
| condiciones_de_pago | Ejemplo: CRÉDITO 15 DÍAS | String | Opcional | 1 hasta 250 |
| generado_por_contingencia | Si está comunicando un comprobante emitido en contingencia debería ser true (en minúsculas). | Boolean | Opcional | Hasta 5 |
| bienes_region_selva | Si el producto es un bien de la región selva debería ser true | Boolean | Opcional | Hasta 5 |
| servicios_region_selva | Si el producto es un servicio de la región selva debería ser true | Boolean | Opcional | Hasta 5 |
| nubecont_tipo_de_venta_codigo | Código del Tipo de Venta registrado en NubeCont, debes enviar el código correcto, de otro modo NubeCont las rechazará. | String | Opcional | Hasta 5 |
| medio_de_pago | Ejemplo: TARJETA VISA OP: 232231 Nota: Si es al Crédito, se debe de usar “venta_al_credito” | String | Opcional | 1 hasta 250 |
| orden_compra_servicio | Ejemplo: 21344 | String | Opcional | 1 hasta 20 |
| placa_vehiculo | Ejemplo: ALF-321 | String | Opcional | 1 hasta 8 |
| observaciones | Texto de 0 hasta 1000 caracteres. Si se desea saltos de línea para la representación impresa o PDF usar <br>. Ejemplo: XXXXX <br> YYYYYY | Text | Opcional | Hasta 5 |

## Sección 12 — Estructuras anidadas

| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| :---- | :---- | :---- | :---- | :---- |
| items | Permite items anidados, se refiere a los ITEMS o LÍNEAS del comprobante, el detalle en un cuadro más abajo. | - | - | - |
| guias | Permite guias anidadas, se refiere a los ITEMS o LÍNEAS del comprobante, el detalle en un cuadro más abajo. | - | - | - |
| venta_al_credito | Permite venta_al_credito anidadas, se refiere a los ITEMS o LÍNEAS del comprobante, el detalle en un cuadro más abajo. | - | - | - |
