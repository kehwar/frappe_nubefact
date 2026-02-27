# DocType: Nubefact API Log

**DocType Name**: `Nubefact API Log`
**Type**: Standard DocType
**Purpose**: Logs all API requests and responses for auditing and troubleshooting.

## Fields

| Field Label | Field Name | Field Type | Required | Description |
|------------|------------|------------|----------|-------------|
| **Request Details** | | Section Break | | |
| Operation | `operation` | Select | Yes | Options: generar_comprobante, consultar_comprobante, generar_anulacion, consultar_anulacion, generar_guia, consultar_guia |
| Branch | `branch` | Link | No | Nubefact Branch used for this API call |
| Reference Delivery Note | `reference_delivery_note` | Link | No | Nubefact Delivery Note this log relates to |
| API Route | `api_route` | Data | No | Effective request route/URL used for API call |
| Request Timestamp | `request_timestamp` | Datetime | Yes | When the request was sent |
| **Response Details** | | Section Break | | |
| Response Timestamp | `response_timestamp` | Datetime | No | When the response was received |
| Response Status Code | `response_status_code` | Int | No | HTTP status code |
| Duration (ms) | `duration_ms` | Int | No | Request duration in milliseconds |
| Status | `status` | Select | No | Options: Success, Error |
| Error Code | `error_code` | Data | No | NubeFact error code if failed |
| Error Message | `error_message` | Text | No | Error message if failed |
| Response Payload | `response_payload` | Code | No | Full JSON response payload |
| **Request Payload** | | Section Break (collapsible) | | |
| Request Payload | `request_payload` | Code | No | Full JSON request payload |

## Settings
- Auto Name: `By script` (generated from `request_timestamp`, with collision suffix when needed)
- Sort Field: `request_timestamp`
- Sort Order: DESC
- Track Changes: Disabled
- Allow Rename: No

## Status Colors
- Success: green
- Error: red

## Permissions
- System Manager: Full access
- Accounts Manager: Read only

## Implementation Status
- ✅ Implemented.
- `create_api_log(...)` is used by `make_request(...)` to persist all API attempts.
- Uses specific `branch` and `reference_delivery_note` links instead of a generic dynamic link.
