# CPE API — ESTRUCTURA DE RESPUESTA DE NUBEFACT PARA ANULACIÓN O COMUNICACIÓN DE BAJA

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA DE LA RESPUESTA DE NUBEFACT PARA ANULACIÓN O COMUNICACIÓN DE BAJA

| ESTRUCTURAS DE JSON DE RESPUESTA DE NUBEFACT PARA ANULACIONES O COMUNICACIONES DE BAJA |  |  |
| :---- | :---- | :---- |
| ATRIBUTO | VALOR | TIPO DE DATO |
| numero | Número del documento generado | Integer |
| enlace | Enlace único NUBEFACT (admite `.pdf`) | String |
| sunat\_ticket\_numero | Ticket asignado por SUNAT | String |
| aceptada\_por\_sunat | false / true | Boolean |
| sunat\_description | Descripción de respuesta/error SUNAT | String |
| sunat\_note | Nota SUNAT | String |
| sunat\_responsecode | Código SUNAT | String |
| sunat\_soap\_error | Errores SOAP de envío SUNAT | String |
| xml\_zip\_base64 | XML zip en base64 (opcional según configuración) | Text |
| pdf\_zip\_base64 | PDF zip en base64 (opcional según configuración) | Text |
| cdr\_zip\_base64 | CDR zip en base64 (opcional según configuración) | Text |
| enlace\_del\_pdf | Enlace de archivo PDF | Text |
| enlace\_del\_xml | Enlace de archivo XML | Text |
| enlace\_del\_cdr | Enlace de archivo CDR | Text |
