# GRE API — PARA DOCUMENTOS RELACIONADOS AL DOCUMENTO

> Source: `assets/gre-manual-google-doc.md` — PARA DOCUMENTOS RELACIONADOS AL DOCUMENTO

| PARA DOCUMENTOS RELACIONADOS AL DOCUMENTO |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| tipo | 01 \= Factura  03 \= Boleta de Venta 09 \= Guía de Remisión Remitente 31 \= Guía de Remisión Transportista  | Integer | Obligatorio | 2 exactos |
| serie | Serie del Documento relacionado  Ejemplo F001, B001 | String | Obligatorio | 4 exactos |
| número | Número correlativo del documento, sin ceros a la izquierda Ejemplo 1, 10, 100 | Integer | Obligatorio | 1 hasta 8 |
