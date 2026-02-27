# GRE API — ESTRUCTURA DE RESPUESTA DE NUBEFACT

> Source: `assets/gre-manual-google-doc.md` — ESTRUCTURA DE RESPUESTA DE NUBEFACT

MUY IMPORTANTE: En ambiente de DEMO las validaciones son parciales (por ejemplo si DNI o RUC existe). En modo PRODUCCIÓN la respuesta será de la SUNAT que tiene una validación más estricta.

| ESTRUCTURAS DE JSON DE RESPUESTA DE NUBEFACT PARA FACTURAS, BOLETAS Y NOTAS |  |  |
| :---- | :---- | :---- |
| ATRIBUTO | VALOR | TIPO DE DATO |
| tipo\_de\_comprobante | Tipo de COMPROBANTE que se generó: 7 \= GUÍA REMISIÓN REMITENTE 8 \= GUÍA REMISIÓN TRANSPORTISTA | Integer |
| serie | Serie de documento generado. | String |
| numero | Número de documento generado. | Integer |
| enlace | ENLACE único asignado por NUBEFACT. Para ver el PDF puedes agregar la extensión .pdf, ejemplo: https://www.nubefact.com/guia/xxxxxxxx**.pdf** https://www.pse.pe/guia/xxxxxxxx**.pdf Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | String |
| aceptada\_por\_sunat | false \= FALSO (En minúsculas) true \= VERDADERO (En minúsculas) | Boolean |
| sunat\_description | Cuando hay errores en la SUNAT se describirá el error | String |
| sunat\_note | Cuando hay errores en la SUNAT se describirá el error | String |
| sunat\_responsecode | Cuando hay errores en la SUNAT se describirá el error | String |
| sunat\_soap\_error | Otros errores que imposibilitan el envío a la SUNAT | String |
| pdf\_zip\_base64 | Contenido del archivo xml zipeado en base64 que puedes almacenar de ser necesario. (Se debe activar esta opción desde "Configuración principal" en NUBEFACT). **Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
| xml\_zip\_base64 | Contenido del archivo pdf zipeado en base64 que puedes almacenar de ser necesario. (Se debe activar esta opción desde "Configuración principal" en NUBEFACT). **Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
| cdr\_zip\_base64 | Contenido del archivo cdr de sunat zipeado en base64 que puedes almacenar de ser necesario. (Se debe activar esta opción desde "Configuración principal" en NUBEFACT). **Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
| cadena\_para\_codigo\_qr | Si tienes tu propia representación impresa, debes generar un QR con este dato. | Text |
| enlace\_del\_pdf | Recibirás el link completo del PDF ya generado: https://www.nubefact.com/guia/xxxxxxxx**.pdf Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
| enlace\_del\_xml | Recibirás el link completo del XML ya generado: https://www.nubefact.com/guia/xxxxxxxx**.xml Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
| enlace\_del\_cdr | Recibirás el link completo el CDR (Constancia de Recepción de SUNAT) si la SUNAT ya respondió: https://www.nubefact.com/guia/xxxxxxxx**.cdr  Sólo si la Guía fue aceptada por la SUNAT, caso contrario no recibirás la respuesta.** | Text |
