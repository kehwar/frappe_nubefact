# DocType Schema: Nubefact Guía de Remisión Conductor Secundario

## Scope

- Child table DocType: `Nubefact Guía de Remisión Conductor Secundario`
- Parent DocType: `Nubefact Guía de Remisión`

## Source Reference

- `gre-api-estructura-conductores-secundarios.md`

## Payload Fields (same naming as GRE reference)

| Atributo | Tipo de dato | Requisito | Longitud |
|---|---|---|---|
| documento_tipo | Integer | Condicional | 1 exacto |
| documento_numero | String | Condicional | 1 hasta 15 |
| nombre | String | Condicional | Hasta 250 |
| apellidos | String | Condicional | Hasta 250 |
| numero_licencia | String | Condicional | 9 hasta 10 |

## Extra Fields (not present in NubeFact payload/response) — English only

None documented in this schema file.
