# CPE API — ESTRUCTURA PARA CONSULTAR FACTURAS, BOLETAS Y NOTAS

> Source: `assets/cpe-manual-google-doc.md` — ESTRUCTURA PARA CONSULTAR FACTURAS, BOLETAS Y NOTAS

| JSON PARA CONSULTAR FACTURAS, BOLETAS Y NOTAS |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| ATRIBUTO | DESCRIPCIÓN | TIPO DE DATO | REQUISITO | LONGITUD |
| operacion | Este valor siempre deberá ser "consultar\_comprobante" | String | Obligatorio | 13 exactos |
| tipo\_de\_comprobante | 1 = FACTURA, 2 = BOLETA, 3 = NOTA DE CRÉDITO, 4 = NOTA DE DÉBITO | Integer | Obligatorio | 1 exacto |
| serie | Empieza con "F" para facturas/notas asociadas; "B" para boletas/notas asociadas | String | Obligatorio | 4 exactos |
| numero | Número correlativo, sin ceros a la izquierda | Integer | Obligatorio | 1 hasta 8 |
