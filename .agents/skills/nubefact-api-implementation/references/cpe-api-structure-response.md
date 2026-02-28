# CPE API — ESTRUCTURA DE RESPUESTA DE NUBEFACT PARA FACTURAS, BOLETAS, NOTAS

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA DE RESPUESTA DE NUBEFACT PARA FACTURAS, BOLETAS, NOTAS

| ESTRUCTURAS DE JSON DE RESPUESTA DE NUBEFACT PARA FACTURAS, BOLETAS Y NOTAS |  |  |
| :---- | :---- | :---- |
| ATRIBUTO | VALOR | TIPO DE DATO |
| tipo\_de\_comprobante | Tipo de comprobante generado (1, 2, 3, 4) | Integer |
| serie | Serie de documento generado | String |
| numero | Número de documento generado | Integer |
| enlace | Enlace único NUBEFACT (admite `.pdf`) | String |
| aceptada\_por\_sunat | false / true | Boolean |
| sunat\_description | Descripción de respuesta/error SUNAT | String |
| sunat\_note | Nota SUNAT | String |
| sunat\_responsecode | Código SUNAT | String |
| sunat\_soap\_error | Errores SOAP de envío SUNAT | String |
| pdf\_zip\_base64 | PDF zip en base64 (opcional según configuración) | Text |
| xml\_zip\_base64 | XML zip en base64 (opcional según configuración) | Text |
| cdr\_zip\_base64 | CDR zip en base64 (opcional según configuración) | Text |
| cadena\_para\_codigo\_qr | Cadena para generar QR | String |
| codigo\_hash | Código hash | String |
| codigo\_de\_barras | Valor para generar PDF417 | String |
| enlace\_del\_pdf | Enlace de archivo PDF | Text |
| enlace\_del\_xml | Enlace de archivo XML | Text |
| enlace\_del\_cdr | Enlace de archivo CDR | Text |
