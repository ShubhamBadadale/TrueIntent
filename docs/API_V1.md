# TrueIntent API v1 — contract reference

Versioned, mobile-ready HTTP contract. The legacy `/check-*` routes return the original flat
bodies and are frozen; everything new should use `/api/v1/*`. Interactive docs with request and
response schemas are served at `/docs` whenever the backend runs.

Base URL (local development): `http://localhost:8000`. Override for deployments; the web portal
reads `VITE_API_URL` at build time and native clients should make it configurable.

## Envelopes

Every v1 success:

```json
{
  "success": true,
  "data": {},
  "meta": {"request_id": "9f2c…", "api_version": "v1"}
}
```

Every v1 failure:

```json
{
  "success": false,
  "error": {
    "code": "invalid_url",
    "message": "Invalid URL. Expected an HTTP(S) address such as https://example.com/login.",
    "module": "module_b",
    "details": {}
  },
  "meta": {"request_id": "9f2c…", "api_version": "v1"}
}
```

- `meta.request_id` always equals the `X-Request-ID` response header. Send your own
  `X-Request-ID` (letters, digits, `.` `_` `:` `-`, max 64 chars) to correlate client logs with
  server logs; anything else is replaced with a generated ID.
- `error.code` is stable and append-only — branch on it, not on `message`.
- `error.message` is safe to display to an end user. It never contains a stack trace, a
  filesystem path, an environment value, or a secret; the suite asserts this on every error path.
- `risk_index` (0–100) is `score` rescaled for display. It is **not calibrated** and must be
  labelled as such in any UI — the web portal renders every value as "Risk Index".

## Endpoints

### `GET /health`

Liveness only: `{"status": "ok"}`. Used by the Docker healthcheck. Says nothing about models.

### `GET /ready`

Readiness with per-component diagnostics. `200` when the API can serve (possibly degraded), `503`
when a component is actively broken.

```json
{
  "success": true,
  "data": {
    "status": "degraded",
    "service": "TrueIntent API",
    "api_version": "v1",
    "degraded": true,
    "generated_at": "2026-10-01T02:29:34+00:00",
    "components": [
      {"name": "module_a", "status": "unavailable", "detail": "Benchmark artifact absent…"},
      {"name": "module_b", "status": "ok", "detail": "URL classifier active."},
      {"name": "module_c", "status": "ok", "detail": "Message model active."},
      {"name": "module_d", "status": "ok", "detail": "Learned fusion policy active."},
      {"name": "ocr", "status": "unavailable", "detail": "Tesseract engine binary not found…"}
    ]
  },
  "meta": {"request_id": "…", "api_version": "v1"}
}
```

Component statuses: `ok` (serves real answers), `degraded` (serves a labelled fallback —
rules-only URL checks, fixed-weight fusion), `unavailable` (its endpoints answer 503 with a
reason), `error` (actively broken, e.g. a corrupt artifact — the deployment is not ready). A fresh
clone without licensed data or an OCR binary reports `degraded` by design; that is the honest
operating mode, not an outage.

### `POST /api/v1/analyze/url`

```json
{ "url": "http://192.168.1.1/verify-account" }
```

Returns `data: {score, risk_index, reasons, ml_status}`. Offline analysis only — the destination
is never fetched, so responses are deterministic. `ml_status` is `"active"` after successful
classifier inference, otherwise `"rules_only (…)"` with the reason.

### `POST /api/v1/analyze/message`

```json
{ "text": "You are under investigation. Stay on the line…" }
```

JSON body — no multipart needed. Returns `data: {score, risk_index, signature, reasons,
ml_status, intent, intent_probabilities, rule_evidence, text_assessed}`. `signature` is one of
`fear_authority`, `greed_opportunity`, `none`; `intent` is the finer ten-class label (or `null` on
legacy artifacts). When no message model is trained the endpoint answers **503**
`message_not_assessed` — a missing assessment is never presented as a low score.

### `POST /api/v1/analyze/image`

Multipart upload, single part named `image`. Accepted: PNG, JPEG, WebP, BMP up to 10 MB and
10 megapixels. The declared content type, filename extension and actual magic bytes must agree —
a mismatch is rejected (415 for an unsupported declared type, 400 for mislabelled bytes), and an
oversized body is rejected (413) before analysis.

Returns the message shape plus `ocr_text` and `ocr_status` (`ok` / `insufficient_text` /
`ocr_unavailable` / `invalid_image`). Short or garbled OCR output returns 200 with score `0.0` and
a "try a clearer screenshot" reason — explicitly not a clean verdict.

### `POST /api/v1/analyze/combined`

```json
{ "url": "http://192.168.1.1/verify-account", "text": "…", "active_call": true }
```

Any subset of `url` / `text`, plus optional user-reported `active_call` (`true` / `false` /
omitted-means-unknown). Returns `data: {tier, score, risk_index, explanation, details, modules}`.
`modules` carries the per-module results; `details` carries the fusion method, caveats and
log-odds contributions. Explanations always name contributing *and* skipped modules.

There is deliberately **no** `transaction` field: sending one fails schema validation (422) with a
hint explaining that Module A is a benchmark, not a fusion input.

### `POST /api/v1/module-a/benchmark`

```json
{ "amount": 500.0, "amount_unit": "ieee_cis_source" }
```

Unlike the legacy route, `amount_unit` has **no default** — a new client must state its units. Only
`ieee_cis_source` is accepted; anything else (including INR) is refused with 422
`amount_unit_rejected`. Without a trained artifact the endpoint answers 503
`model_unavailable`. Success returns `{score, analysis_scope, explanation}` — deliberately *no*
`risk_index`, because a benchmark score is not a risk tier.

### `GET /api/v1/module-a/contract`

Returns the exact versioned feature contract an artifact must satisfy
(`{version, features, amount_unit, scope}`), so a client can discover it instead of hardcoding it.

## Error codes

| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `missing_input` | Required input absent (e.g. no text, no image) |
| 400 | `conflicting_input` | Mutually exclusive inputs (legacy text+image) |
| 400 | `unreadable_image` | Bytes are not a readable image, or contradict the declared type |
| 404 | `not_found` | Unknown endpoint |
| 405 | `method_not_allowed` | Wrong method for the endpoint |
| 413 | `payload_too_large` | Body or upload exceeds the configured limit |
| 415 | `unsupported_media_type` | Declared upload type outside PNG/JPEG/WebP/BMP |
| 422 | `validation_error` | Schema violation; `details.fields` lists `{field, message, type}` without echoing values |
| 422 | `invalid_url` | Malformed URL (`module: module_b`), with the character limit in `details` |
| 422 | `transaction_fusion_disabled` | Transaction-bearing combined request on legacy routes |
| 422 | `amount_unit_rejected` | Non-source-unit benchmark amount (`module: module_a`) |
| 503 | `ocr_unavailable` | Screenshot path without a Tesseract engine (`module: module_c`) |
| 503 | `message_not_assessed` | Text was never scored; never a low score (`module: module_c`) |
| 503 | `model_unavailable` / `artifact_incompatible` | Artifact missing or corrupt |
| 500 | `internal_error` | Unexpected failure; retry quoting `meta.request_id` |

## Mobile integration notes

1. **Health-check against `/ready`, not `/health`.** Gate message/image features on the `module_c`
   and `ocr` component statuses instead of discovering 503s at runtime; hide the benchmark tab
   when `module_a` is `unavailable`.
2. **Send `X-Request-ID`.** On any 500, surface the ID with a retry prompt — server logs carry the
   same ID with the full traceback.
3. **Upload flow:** POST the screenshot to `/analyze/image` first. If `ocr_status` is not `ok`,
   show the reason (or fall back to typed text) rather than combining — the web portal follows
   exactly this sequence before calling `/analyze/combined`.
4. **Never cache `risk_index` as a verdict.** It is uncalibrated; the portal pairs every value
   with safety guidance and a "not a calibrated probability" note.
5. **Timeouts:** analysis is synchronous per request; allow ~90 s for screenshots (OCR
   subprocess), less for text/URL. The server bounds uploads (10 MB), images (10 MP) and whole
   bodies (12 MB) and aborts oversized reads early.
6. **Offline-first copy:** `ml_status` starting with `rules_only`, `text_assessed: false`, and any
   `degraded: true` readiness flag all mean "the server told you what it could not see" — render
   that state, don't hide it.
