# CPE API — ESTRUCTURA PARA CONSULTAR ANULACIÓN O COMUNICACIÓN DE BAJA

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA PARA CONSULTAR ANULACIÓN O COMUNICACIÓN DE BAJA

| JSON PARA CONSULTAR ANULACIONES O COMUNICACIONES DE BAJA |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| ATRIBUTO | DESCRIPCIÓN | TIPO DE DATO | REQUISITO | LONGITUD |
| operacion | Este valor siempre deberá ser "consultar\_anulacion" | String | Obligatorio | 19 exactos |
| tipo\_de\_comprobante | 1 = FACTURA, 2 = BOLETA, 3 = NOTA DE CRÉDITO, 4 = NOTA DE DÉBITO | Integer | Obligatorio | 1 exacto |
| serie | Empieza con "F" para facturas/notas asociadas; "B" para boletas/notas asociadas | String | Obligatorio | 4 exactos |
| numero | Número correlativo, sin ceros a la izquierda | Integer | Obligatorio | 1 hasta 8 |
