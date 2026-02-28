# CPE API — ESTRUCTURA PARA GENERAR ANULACIÓN O COMUNICACIÓN DE BAJA

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA PARA GENERAR ANULACIÓN O COMUNICACIÓN DE BAJA

| ESTRUCTURA Y VALIDACIONES DE ARCHIVOS JSON PARA GENERAR ANULACIONES O COMUNICACIONES DE BAJA |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| ATRIBUTO | VALOR | TIPO DE DATO | REQUISITO | LONGITUD |
| operacion | Este valor siempre deberá ser "generar\_anulacion" | String | Obligatorio | 17 exactos |
| tipo\_de\_comprobante | 1 = FACTURA, 2 = BOLETA, 3 = NOTA DE CRÉDITO, 4 = NOTA DE DÉBITO | Integer | Obligatorio | 1 exacto |
| serie | Serie del documento a anular | String | Obligatorio | 4 exactos |
| numero | Número del documento a anular | Integer | Obligatorio | 1 hasta 8 |
| motivo | Motivo de anulación | String | Obligatorio | Hasta 100 |
| codigo\_unico | Código único de control generado por el sistema cliente | String | Opcional | Hasta 250 |
