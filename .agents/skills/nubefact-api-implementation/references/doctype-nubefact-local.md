# DocType: Nubefact Local

**DocType Name**: `Nubefact Local`
**Type**: Standard DocType
**Purpose**: Stores per-local NubeFact API credentials and route.

## Frappe-spec Fields (non-API)

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Title | `title` | Data | Yes | Human-friendly local name. |
| Company | `company` | Link | No | Optional ERP company mapping. |

## API-spec Fields (NubeFact-aligned)

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Dirección | `direccion` | Small Text | No | Local address. |
| Ubigeo | `ubigeo` | Data | No | SUNAT ubigeo code for local location. |
| Código SUNAT | `codigo_sunat` | Data | No | SUNAT establishment code for local. |
| Departamento | `departamento` | Data | No | Departamento/región. |
| Provincia | `provincia` | Data | No | Provincia/ciudad. |
| Distrito | `distrito` | Data | No | Distrito. |
| Ruta API | `ruta_api` | Data | Yes | Client route appended to API base URL (or absolute URL). |
| Token API | `token_api` | Password | Yes | Authorization token used in request header. |

## Implementation Status
- ✅ Implemented
- Used directly by `get_request_config()` in API request flow.
