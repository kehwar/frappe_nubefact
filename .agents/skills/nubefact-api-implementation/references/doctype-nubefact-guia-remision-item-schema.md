# DocType Schema: Nubefact Guía de Remisión Ítem

## Scope

- Child table DocType: `Nubefact Guía de Remisión Ítem`
- Parent DocType: `Nubefact Guía de Remisión`

## Source Reference

- `gre-api-estructura-items.md`

## Payload Fields (same naming as GRE reference)

| Atributo | Tipo de dato | Requisito | Longitud |
|---|---|---|---|
| unidad_de_medida | String | Obligatorio | 2 hasta 5 |
| codigo | String | Opcional | 1 hasta 250 |
| descripcion | Text | Obligatorio | 1 hasta 250 |
| cantidad | Numeric | Obligatorio | 1 hasta 12 enteros, hasta con 10 decimales |
| codigo_dam | String | Condicional | 23 caracteres |

## Extra Fields (not present in NubeFact payload/response) — English only

None documented in this schema file.
