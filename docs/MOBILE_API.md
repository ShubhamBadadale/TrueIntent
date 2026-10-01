# TrueIntent Mobile API (`/api/v1`)

Two mobile endpoints share one service (`backend/app/services.py::analyze_mobile`)
and one fusion layer (Module D). Interactive documentation with schemas and
examples is served at `/docs` (Swagger UI) and `/redoc`.

A working client lives in `../mobile/` (React Native + Expo + TypeScript).

## Endpoints

| Method & path | Content-Type | Use |
|---|---|---|
| `POST /api/v1/analyze` | `application/json` | URL and/or message text |
| `POST /api/v1/analyze/screenshot` | `multipart/form-data` | Screenshot plus optional URL/message |

Both return the same envelope: `{"success": true, "data": {...}, "meta": {...}}`.
Failures return `{"success": false, "error": {"code", "message", "module", "details"}, "meta": {...}}`
with the request ID echoed in the `X-Request-ID` header and in `meta`.

## JSON examples

URL + message text:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com/login",
       "message": "Your account will be suspended, verify now."}'
```

Message only (`text` is accepted as an alias of `message`; the two must not disagree):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hey, are we still meeting for lunch tomorrow?"}'
```

URL only, with user-reported call context (`active_call` is unverified input,
never proof of a call):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.google.com/", "active_call": false}'
```

## Screenshot example (multipart)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/screenshot \
  -F 'image=@chat.png;type=image/png' \
  -F 'url=https://example.com/login' \
  -F 'active_call=false'
```

- File field: `image` (`screenshot` accepted as an alias; not both).
- Optional form fields: `url`, `message` (or `text`), `active_call` (`'true'`/`'false'`).
- Images must be PNG/JPEG/WebP/BMP with matching magic bytes; max size is the
  `image_bytes` limit reported by `GET /ready` configuration (default 10 MB).

## Response fields (`data`)

| Field | Meaning |
|---|---|
| `risk_level` / `tier` | `Low` / `Medium` / `High` / `Critical` (same value twice for compatibility) |
| `score` / `risk_index` | Overall risk score 0–1 and its 0–100 rescaling. **Uncalibrated**: it rescales the number, it never claims a fraud probability. |
| `summary` | One-line verdict for small screens, e.g. `"High risk (risk score 0.72): based on URL and message evidence."` |
| `explanation` | Longer plain-language reasoning |
| `evidence` | `[{module, finding}]` fused findings, most incriminating first |
| `url_findings` / `message_findings` / `ocr_findings` | Per-channel results; `null` when that input was not submitted |
| `analyzed_modules` / `contributing_modules` / `unavailable_modules` | Which modules ran; missing information stays missing and is listed, never scored as zero |
| `warnings` | Run-specific notes (partial evidence, unverified call status, fusion method) |
| `limitations` | Standing product limitations (offline URL checks, E2E channels unobservable, …) |
| `recommended_action` / `safety_actions` | Prose guidance plus a per-level checklist |
| `fusion_version`, `details` | Fusion contract version and debug details |

## Timeouts (client guidance)
| Request type | Suggested client timeout |
|---|---|
| JSON (`/analyze`) | 30 s |
| Screenshot (`/analyze/screenshot`) | 60 s (OCR runs server-side with a bounded `ocr_timeout_seconds` limit) |

The server additionally gates request size (`max_request_bytes`, default 12 MB)
and reads uploads in bounded chunks, so oversized bodies fail fast with `413`.

## Development networking

The mobile app takes its backend address from a single environment value —
`EXPO_PUBLIC_API_BASE_URL` (`EXPO_PUBLIC_TRUEINTENT_API_URL` is a legacy
alias) — read once in `mobile/constants/config.ts`. No source file names a
host, so switching environments is a rebuild with a new value, never an edit.

| Environment | Base URL | Notes |
|---|---|---|
| Android emulator | `http://10.0.2.2:8000` | The emulator is a VM: `10.0.2.2` aliases the PC's loopback. |
| iOS simulator / Expo web | `http://127.0.0.1:8000` | Shares the Mac/PC loopback. |
| Expo Go on a physical phone | `http://<pc-lan-ip>:8000` | Same Wi-Fi; backend must bind LAN (`--host 0.0.0.0` or `TRUEINTENT_HOST=0.0.0.0`); open the firewall port. |
| Deployed backend | `https://api.example.com` | Public TLS URL; cert failures surface as `offline` with retry. |

Why `localhost` fails on a physical phone: `localhost` / `127.0.0.1` always
means "this device itself". On the emulator that is the virtual phone (hence
the `10.0.2.2` alias); on a physical phone it is the phone's own loopback,
which never reaches your development PC. Use the PC's LAN IP instead (find it
with `ipconfig` on Windows / `ip addr` on Linux) and keep both devices on the
same network.

## Versioning

- All mobile routes live under `/api/v1`. Breaking changes ship as `/api/v2`;
  additive fields may appear inside `data`/`details` without a version bump.
- `/check-*` routes are frozen legacy and are not part of the mobile contract.

## Error codes you should handle

| HTTP | `code` | When |
|---|---|---|
| 400 | `missing_input` | Nothing submitted (multipart with no fields/file) |
| 400 | `conflicting_input` | `message` vs `text`, or `image` vs `screenshot`, disagree |
| 400 / 415 | `unreadable_image` / `unsupported_media_type` | Bad screenshot bytes or type |
| 413 | `payload_too_large` | Body or image exceeds limits (`details` carries them) |
| 422 | `validation_error` / `invalid_url` | Empty/oversize/invalid input; `details.fields` names the field (never echoes values) |
| 503 | `message_not_assessed` | Text submitted but the message model is unavailable — never treated as safe |
| 503 | `ocr_unavailable` | Screenshot submitted but OCR is down — paste the text instead |
| 503 | `model_unavailable` / `artifact_incompatible` | A model/artifact this deployment needs is missing or incompatible |
