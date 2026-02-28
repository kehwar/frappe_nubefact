# CPE API — PARA ITEMS O LÍNEAS DEL DOCUMENTO

> Source: `assets/cpe-manual-google-doc.md` — PARA ITEMS O LÍNEAS DEL DOCUMENTO

| PARA ITEMS O LÍNEAS DEL DOCUMENTO |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| unidad\_de\_medida | NIU = PRODUCTO ZZ = SERVICIO | String | Obligatorio | 2 hasta 5 |
| codigo | Código interno del producto o servicio | String | Opcional | 1 hasta 250 |
| descripcion | Descripción del producto o servicio | Text | Obligatorio | 1 hasta 250 |
| cantidad | Ejemplo: 1.215 | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 10 decimales |
| valor\_unitario | Sin IGV | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 10 decimales |
| precio\_unitario | Con IGV | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 10 decimales |
| descuento | Descuento de línea (antes de impuestos) | Numeric | Opcional | 1 hasta 12 enteros, hasta con 2 decimales |
| subtotal | Valor unitario por cantidad menos descuento | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 2 decimales |
| tipo\_de\_igv | 1..20 según catálogo del manual (gravado, exonerado, inafecto, exportación, gratuita) | Integer | Obligatorio | 1 hasta 2 enteros |
| tipo\_de\_ivap | 17 = IVAP Gravado, 101 = IVAP Gratuito | String | Opcional | - |
| igv | Total del IGV de la línea | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 2 decimales |
| impuesto\_bolsas | Impuesto de bolsas plásticas | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| total | Total de la línea | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 2 decimales |
| anticipo\_regularizacion | false = FALSO, true = VERDADERO | Boolean | Obligatorio | Hasta 5 |
| anticipo\_documento\_serie | Serie del documento que contiene anticipo | String | Condicional | 4 exactos |
| anticipo\_documento\_numero | Número del documento que contiene anticipo | Integer | Condicional | 1 hasta 8 |
| codigo\_producto\_sunat | Código de producto SUNAT | String | Opcional | Hasta 8 |
| tipo\_de\_isc | Tipo de ISC (1, 2 o 3) | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
| isc | Monto de ISC por línea | Numeric | Condicional | 1 hasta 12 enteros con 2 decimales |
