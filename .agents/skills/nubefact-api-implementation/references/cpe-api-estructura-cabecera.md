# CPE API — ESTRUCTURA PARA GENERAR FACTURAS, BOLETAS Y NOTAS

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA PARA GENERAR FACTURAS, BOLETAS Y NOTAS (CABECERA DEL DOCUMENTO)

| CABECERA DEL DOCUMENTO |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| operación | Este valor siempre deberá ser "generar\_comprobante" para enviar FACTURAS, BOLETAS, NOTAS DE CRÉDITO o DÉBITO | String | Obligatorio | 11 exactos |
| tipo\_de\_comprobante | Tipo de COMPROBANTE que desea generar: 1 = FACTURA 2 = BOLETA 3 = NOTA DE CRÉDITO 4 = NOTA DE DÉBITO | Integer | Obligatorio | 1 exacto |
| serie | Empieza con "F" para FACTURAS y NOTAS ASOCIADAS. Empieza con "B" para BOLETAS DE VENTA y NOTAS ASOCIADAS Si está comunicando un comprobante emitido en contingencia, la serie debe empezar NO debe empezar con "F" ni con "B". Debería empezar con "0", ejemplo: "0001" | String | Obligatorio | 4 exactos |
| número | Número correlativo del documento, sin ceros a la izquierda | Integer | Obligatorio | 1 hasta 8 |
| sunat\_transaction | La mayoría de veces se usa el 1, las demás son para tipos de operaciones muy especiales: 1 = VENTA INTERNA 2 = EXPORTACIÓN 4 = VENTA INTERNA – ANTICIPOS 29 = VENTAS NO DOMICILIADOS QUE NO CALIFICAN COMO EXPORTACIÓN 30 = OPERACIÓN SUJETA A DETRACCIÓN 33 = DETRACCIÓN - SERVICIOS DE TRANSPORTE CARGA 34 = OPERACIÓN SUJETA A PERCEPCIÓN 32 = DETRACCIÓN - SERVICIOS DE TRANSPORTE DE PASAJEROS 31 = DETRACCIÓN - RECURSOS HIDROBIOLÓGICOS 35 = VENTA NACIONAL A TURISTAS - TAX FREE | Integer | Obligatorio | 1 hasta 2 |
| cliente\_tipo\_de\_documento | 6 = RUC - REGISTRO ÚNICO DE CONTRIBUYENTE 1 = DNI - DOC. NACIONAL DE IDENTIDAD - = VARIOS - VENTAS MENORES A S/.700.00 Y OTROS 4 = CARNET DE EXTRANJERÍA 7 = PASAPORTE A = CÉDULA DIPLOMÁTICA DE IDENTIDAD B = DOC.IDENT.PAIS.RESIDENCIA-NO.D 0 = NO DOMICILIADO, SIN RUC (EXPORTACIÓN) G = Salvoconducto | String | Obligatorio | 1 exacto |
| cliente\_numero\_de\_documento | Ejemplo: RUC del CLIENTE, número de DNI, Etc. | String | Obligatorio | 1 hasta 15 |
| cliente\_denominacion | Razón o nombre completo del CLIENTE. | String | Obligatorio | 1 hasta 100 |
| cliente\_direccion | Dirección completa (OPCIONAL en caso de ser una BOLETA DE VENTA o NOTA ASOCIADA). | String | Obligatorio | 1 hasta 100 |
| cliente\_email | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente\_email\_1 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| cliente\_email\_2 | Dirección de email debe ser válido. | String | Opcional | 1 hasta 250 |
| fecha\_de\_emision | Debe ser la fecha actual. Formato DD-MM-AAAA Ejemplo: 10-05-2017 | Date | Obligatorio | 10 exactos |
| fecha\_de\_vencimiento | Deber ser fecha posterior a la fecha de emisión | Date | Opcional | 10 exactos |
| moneda | 1 = SOLES 2 = DÓLARES 3 = EUROS 4 = LIBRA ESTERLINA | Integer | Obligatorio | 1 exacto |
| tipo\_de\_cambio | Ejemplo: 3.421 | Numeric | Condicional | 1 entero con 3 decimales |
| porcentaje\_de\_igv | Ejemplo: 18.00 | Numeric | Obligatorio | 1 hasta 2 enteros con 2 decimales |
| descuento\_global | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_descuento | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_anticipo | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_gravada | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_inafecta | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_exonerada | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_igv | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_gratuita | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_otros\_cargos | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_isc |  | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total | Ejemplo: 1305.05 | Numeric | Obligatorio | 1 hasta 12 enteros con 2 decimales |
| percepcion\_tipo | 1 = PERCEPCIÓN VENTA INTERNA - TASA 2% 2 = PERCEPCIÓN ADQUISICIÓN DE COMBUSTIBLE - TASA 1% 3 = PERCEPCIÓN REALIZADA AL AGENTE DE PERCEPCIÓN CON TASA ESPECIAL - TASA 0.5% | Integer | Condicional | 1 exacto |
| percepcion\_base\_imponible | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_percepcion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_incluido\_percepcion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| retencion\_tipo | 1 = TASA 3% 2 = TASA 6% | Integer | Condicional | 1 exacto |
| retencion\_base\_imponible | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_retencion | Ejemplo: 1305.05 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total\_impuestos\_bolsas | Ejemplo: 0.10 | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| observaciones | Texto de 0 hasta 1000 caracteres. Si se desea saltos de línea para la representación impresa o PDF usar `<br>`. | Text | Opcional | Hasta 5 |
| documento\_que\_se\_modifica\_tipo | 1 = FACTURAS ELECTRÓNICAS 2 = BOLETAS DE VENTA ELECTRÓNICAS | Integer | Condicional | 1 exacto |
| documento\_que\_se\_modifica\_serie | SERIE de la FACTURA o BOLETA que se modifica | String | Condicional | 4 exactos |
| documento\_que\_se\_modifica\_numero | NÚMERO de la FACTURA o BOLETA que se modifica | Integer | Condicional | 1 hasta 8 |
| tipo\_de\_nota\_de\_credito | 1 = ANULACIÓN DE LA OPERACIÓN 2 = ANULACIÓN POR ERROR EN EL RUC 3 = CORRECCIÓN POR ERROR EN LA DESCRIPCIÓN 4 = DESCUENTO GLOBAL 5 = DESCUENTO POR ÍTEM 6 = DEVOLUCIÓN TOTAL 7 = DEVOLUCIÓN POR ÍTEM 8 = BONIFICACIÓN 9 = DISMINUCIÓN EN EL VALOR 10 = OTROS CONCEPTOS 11 = AJUSTES AFECTOS AL IVAP 12 = AJUSTES DE OPERACIONES DE EXPORTACIÓN 13 = AJUSTES - MONTOS Y/O FECHAS DE PAGO | Integer | Condicional | 1 hasta 2 |
| tipo\_de\_nota\_de\_debito | 1 = INTERESES POR MORA 2 = AUMENTO DE VALOR 3 = PENALIDADES 4 = AJUSTES AFECTOS AL IVAP 5 = AJUSTES DE OPERACIONES DE EXPORTACIÓN | Integer | Condicional | 1 exacto |
| enviar\_automaticamente\_a\_la\_sunat | false = FALSO true = VERDADERO | Boolean | Condicional | Hasta 5 |
| enviar\_automaticamente\_al\_cliente | false = FALSO true = VERDADERO | Boolean | Condicional | Hasta 5 |
| codigo\_unico | Usarlo sólo si deseas que controlemos la generación de documentos. | String | Opcional | 1 hasta 20 |
| condiciones\_de\_pago | Ejemplo: CRÉDITO 15 DÍAS | String | Opcional | 1 hasta 250 |
| medio\_de\_pago | Ejemplo: TARJETA VISA OP: 232231 | String | Opcional | 1 hasta 250 |
| placa\_vehiculo | Ejemplo: ALF-321 | String | Opcional | 1 hasta 8 |
| orden\_compra\_servicio | Ejemplo: 21344 | String | Opcional | 1 hasta 20 |
| detraccion | false = FALSO true = VERDADERO | Boolean | Condicional | Hasta 5 |
| detraccion\_tipo | Tipos de detracción SUNAT (001, 002, 003, ..., 045 según manual) | Integer | Condicional | 1 hasta 2 |
| detraccion\_total | Total de la Detracción | Numeric | Condicional | 1 hasta 12 enteros, hasta con 10 decimales |
| detraccion\_porcentaje | Porcentaje Detracción | Numeric | Condicional | 1 hasta 3 enteros, hasta con 5 decimales |
| medio\_de\_pago\_detraccion | Medios de pago SUNAT (001, 002, ..., 999 según manual) | Numeric | Condicional | 1 hasta 2 |
| ubigeo\_origen | Código de Ubigeo de Origen | Integer | Condicional | 6 exactos |
| direccion\_origen | Dirección completa del origen | String | Condicional | 1 hasta 100 |
| ubigeo\_destino | Código de Ubigeo de Destino | Integer | Condicional | 6 exactos |
| direccion\_destino | Dirección completa del destino | String | Condicional | 1 hasta 100 |
| detalle\_viaje | Detalle del transporte | String | Condicional | 1 hasta 100 |
| val\_ref\_serv\_trans | Valor referencia del servicio de transporte | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val\_ref\_carga\_efec | Valor referencial carga efectiva | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val\_ref\_carga\_util | Valor referencial carga útil | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| punto\_origen\_viaje | Punto de origen del viaje | Integer | Condicional | 6 exactos |
| punto\_destino\_viaje | Punto de destino del viaje | Integer | Condicional | 6 exactos |
| descripcion\_tramo | Descripción del tramo | String | Condicional | 1 hasta 100 |
| val\_ref\_carga\_efec\_tramo\_virtual | Valor preliminar referencial sobre la carga efectiva | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| configuracion\_vehicular | Configuración vehicular del vehículo | String | Condicional | Hasta 15 |
| carga\_util\_tonel\_metricas | Carga útil en toneladas métricas | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| carga\_efec\_tonel\_metricas | Carga efectiva en toneladas métricas | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| val\_ref\_tonel\_metrica | Valor referencial por tonelada métrica | Numeric | Condicional | 1 hasta 5 |
| val\_pre\_ref\_carga\_util\_nominal | Valor preliminar referencial por carga útil nominal | Numeric | Condicional | 1 hasta 12 enteros, hasta con 2 decimales |
| indicador\_aplicacion\_retorno\_vacio | Indicador de aplicación de factor retorno al vacío | Boolean | Condicional | Hasta 5 |
| matricula\_emb\_pesquera | Matrícula de embarcación pesquera | String | Condicional | Hasta 15 |
| nombre\_emb\_pesquera | Nombre de embarcación pesquera | String | Condicional | Hasta 50 |
| descripcion\_tipo\_especie\_vendida | Descripción tipo de especie vendida | String | Condicional | Hasta 100 |
| lugar\_de\_descarga | Lugar de descarga | String | Condicional | Hasta 200 |
| cantidad\_especie\_vendida | Cantidad de especie vendida | Numeric | Condicional | 12 enteros, hasta con 2 decimales |
| fecha\_de\_descarga | Fecha de descarga. Formato AAAA-MM-DD | Date | Condicional | 10 exactos |
| formato\_de\_pdf | Formato PDF (A4, A5 o TICKET) | String | Opcional | 2 hasta 5 |
| generado\_por\_contingencia | Si comunica comprobante por contingencia, usar true | Boolean | Opcional | Hasta 5 |
| bienes\_region\_selva | Si es bien de región selva, usar true | Boolean | Opcional | Hasta 5 |
| servicios\_region\_selva | Si es servicio de región selva, usar true | Boolean | Opcional | Hasta 5 |
| nubecont\_tipo\_de\_venta\_codigo | Código de tipo de venta registrado en NubeCont | String | Opcional | Hasta 5 |
| items | Permite items anidados (detalle en tabla aparte) | - | - | - |
| guias | Permite guías anidadas (detalle en tabla aparte) | - | - | - |
| venta\_al\_credito | Permite cuotas de venta al crédito (detalle en tabla aparte) | - | - | - |
