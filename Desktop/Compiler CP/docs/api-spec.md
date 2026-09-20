# API Spec

## `POST /api/compile`

Request:

```json
{ "source": "cloud app ...", "target": "aws" }
```

`target` may be `aws`, `gcp`, `azure`, or `all`.

Response:

```json
{
  "success": true,
  "diagnostics": [],
  "ast": {},
  "ir": { "nodes": [], "edges": [] },
  "generated": { "aws": "...", "gcp": null, "azure": null },
  "report": { "phase_timings_ms": {}, "resource_counts": {} }
}
```

Syntax and semantic errors return HTTP 200 with `success: false`; malformed HTTP payloads return 422.

## `GET /api/examples`

Returns the checked-in `.mcd` examples used by the compiler tests.

## `POST /api/validate-terraform`

Validates generated HCL with Terraform/OpenTofu when available on the server.
