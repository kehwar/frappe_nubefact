# DocType: Nubefact Branch

**DocType Name**: `Nubefact Branch`
**Type**: Standard DocType
**Purpose**: Stores per-branch NubeFact API credentials and route.

## Current Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| Title | `title` | Data | Yes | Human-friendly branch name. |
| Company | `company` | Link | No | Optional ERP company mapping. |
| Address | `address` | Small Text | No | Branch address. |
| Ubigeo | `ubigeo` | Data | No | SUNAT ubigeo code for branch location. |
| SUNAT Code | `sunat_code` | Data | No | SUNAT establishment code for branch. |
| State | `state` | Data | No | State/region. |
| City | `city` | Data | No | City. |
| County | `county` | Data | No | District/county. |
| API Route | `api_route` | Data | Yes | Client route appended to API base URL (or absolute URL). |
| API Token | `api_token` | Password | Yes | Authorization token used in request header. |

## Implementation Status
- ✅ Implemented
- Used directly by `get_request_config()` in API request flow.
