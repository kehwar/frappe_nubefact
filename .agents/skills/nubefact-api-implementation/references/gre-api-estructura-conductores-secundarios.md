# GRE API — PARA CONDUCTORES SECUNDARIOS

> Source: `assets/gre-manual-google-doc.md` — PARA CONDUCTORES SECUNDARIOS - OPCIONAL (Máximo hasta 2 Conductores)

| PARA CONDUCTORES SECUNDARIOS \- OPCIONAL (Máximo hasta 2 Conductores) |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- |
| **ATRIBUTO** | **VALOR** | **TIPO DE DATO** | **REQUISITO** | **LONGITUD** |
| documento\_tipo | 1 \= DNI \- DOC. NACIONAL DE IDENTIDAD 4 \= CARNET DE EXTRANJERÍA 7 \= PASAPORTE A \= CÉDULA DIPLOMÁTICA DE IDENTIDAD 0 \= NO DOMICILIADO, SIN RUC (EXPORTACIÓN) Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". | Integer | Condicional | 1 exacto |
| documento\_numero | Ejemplo: Número de DNI, Etc. Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". | String | Condicional | 1 hasta 15 |
| nombre | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". | String | Condicional | Hasta 250 |
| apellidos | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". | String | Condicional | Hasta 250 |
| numero\_licencia | Es obligatorio Si el tipo de transporte es PRIVADO Para GRE Remitente: sólo cuando 'tipo\_de\_transporte' es "02". | String | Condicional | 9 hasta 10 |
