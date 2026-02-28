# GRE API — ESTRUCTURA PARA CONSULTAR GRE REMITENTE O TRANSPORTISTA

> Source: `assets/gre-manual-google-doc.md` — OPERACIÓN: CONSULTAR GRE REMITENTE O TRANSPORTISTA

| JSON PARA CONSULTAR GRE REMITENTE O TRANSPORTISTA |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| ATRIBUTO | DESCRIPCIÓN | TIPO DE DATO | REQUISITO | LONGITUD |
| operacion | Este valor siempre deberá ser `consultar_guia`. | String | Obligatorio | 13 exactos |
| tipo_de_comprobante | Tipo de comprobante de la GRE a consultar: 7 = GUÍA DE REMISIÓN REMITENTE, 8 = GUÍA DE REMISIÓN TRANSPORTISTA. | Integer | Obligatorio | 1 exacto |
| serie | Serie de la GRE a consultar. Para remitente inicia con `T` (ej. `TTT1`) y para transportista con `V` (ej. `VVV1`). | String | Obligatorio | 4 exactos |
| numero | Número correlativo del documento, sin ceros a la izquierda. | Integer | Obligatorio | 1 hasta 8 |

> Nota: la estructura de respuesta de esta operación se documenta en `references/gre-api-estructura-respuesta.md`.
