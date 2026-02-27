# GRE API — PARA ITEMS O LÍNEAS DEL DOCUMENTO

> Source: `assets/gre-manual-google-doc.md` — PARA ITEMS O LÍNEAS DEL DOCUMENTO

| PARA ITEMS O LÍNEAS DEL DOCUMENTO |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| unidad\_de\_medida | NIU \= PRODUCTO ZZ \= SERVICIO Si necesitas más unidades de medida, debes crearlas primeramente en tu cuenta de NUBEFACT para que estén disponibles.En caso de que el motivo sea **Importación** o **Exportación** debe usar las unidades de medida del **Catálogo 65 de la SUNAT:  Código de unidades de medida (para uso solo para la GRE en DAM o DS)https://cpe.sunat.gob.pe/node/116** | String | Obligatorio | 2 hasta 5 |
| codigo | Código interno del producto o servicio, asignado por ti. Ejemplo: C001 | String | Opcional | 1 hasta 250 |
| descripcion | Descripción del producto o servicio. Ejemplo: SERVICIO DE REPARACIÓN DE PC, ETC. | Text | Obligatorio | 1 hasta 250 |
| cantidad | Ejemplo: 1.215 | Numeric | Obligatorio | 1 hasta  12 enteros, hasta con  10 decimales |
| codigo\_dam | **Solo para motivo de traslado exportación o importación:****a) Ejemplo (DAM):**xxxx(serie)/xxx-xxxx-10-xxxxxx(DAM)  1/123-1234-10-123456 **b) Ejemplo (DS):** xxxx(serie)/xxx-xxxx-18-xxxxxx(DS)  1/123-1234-18-123456 | String | Condicional | 23 caracteres |
