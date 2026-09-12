# TrueIntent — 5-Minute Live Demo Script (v1.0)

All inputs/outputs below were rehearsed against the real backend on 2026-09-12.
UI path and API path are interchangeable (the portal calls these exact endpoints —
proven by `tests/test_integration.py::test_frontend_api_client_matches_backend_routes`).
If the UI ever stalls, run the `curl` fallback for that step and keep going.

## 0:00 — Setup (do before the audience arrives)

```bash
# Terminal 1 — backend (http://localhost:8000, docs at /docs)
.\run-backend.ps1            # or:  docker compose up --build
# Terminal 2 — frontend (http://localhost:5173)
.\run-frontend.ps1
```

Pre-flight (must return `{"status":"ok"}`):

```bash
curl http://localhost:8000/health
```

Say (30s): *"Banks verify **who** you are. Nobody verifies **why** you're sending the money.
TrueIntent correlates what you're doing with what you're being told — and explains itself
in plain words. Three checks, one verdict."*

## 0:30 — (a) A clean transaction scores Low

UI: **Transaction** tab → amount `500`, call **off**, device `dev_0001` → *Check this situation*.
Fallback:

```bash
curl -X POST http://localhost:8000/check-transaction -H "Content-Type: application/json" \
  -d '{"amount":500,"timestamp":"2026-09-12T14:00:00Z","device_id":"dev_0001","is_active_call":false,"transaction_velocity":1}'
```

Expect: `score` **0.0066** → tier **Low**. Say: *"An ordinary daytime transfer. Nothing to flag —
note the system says why, not just a number."*

## 1:30 — (b) A suspicious URL gets flagged

UI: **Link** tab → paste `http://192.168.1.1/verify-account` → *Check this link*.
Fallback: `POST /check-url` with `{"url":"http://192.168.1.1/verify-account"}`.

Expect: score **0.6** with reasons *"Insecure protocol…"* and
*"Host is a raw IP address (192.168.1.1)…"*. Say: *"No domain name, no encryption —
two structural tells, no machine learning needed."*

## 2:30 — (c) A scam message is flagged with its signature type

UI: **Message** tab → paste `You are under investigation. Stay on the line and do not disconnect.`
Fallback: `POST /check-message` (form field `text`) with the same string.

Expect: score **0.9**, signature **`fear_authority`**, four matched-phrase reasons
(*'under investigation'*, *'stay on the line'*, *'do not disconnect'*, *'you are under'*).
Say: *"This is the digital-arrest script. The system names the tactic — fear/authority —
not just 'scam'."* (A trading-style message would return `greed_opportunity` instead.)

## 3:30 — (d) THE THESIS MOMENT: combined signals escalate to High ★

Say: *"Now the point of the whole project. This transfer on its own — ₹8,000, daytime,
known device, even **with an active call** — scores **Low (0.007)**. A bank sees nothing wrong.
Watch what happens when we correlate it with the coercion."*

UI: **Transaction** tab (or `POST /check-combined`) with all three at once:
- transaction: `{"amount":8000,"timestamp":"2026-09-12T14:00:00Z","device_id":"dev_0001","is_active_call":true,"transaction_velocity":2}`
- url: `http://hdfcbaank-secure-login-verify.xyz/update-your-account-now-please-urgent`
- text: `You are under investigation. Stay on the line and do not disconnect.`

Fallback:

```bash
curl -X POST http://localhost:8000/check-combined -H "Content-Type: application/json" -d ^
  "{\"transaction\":{\"amount\":8000,\"timestamp\":\"2026-09-12T14:00:00Z\",\"device_id\":\"dev_0001\",\"is_active_call\":true,\"transaction_velocity\":2},^
   \"url\":\"http://hdfcbaank-secure-login-verify.xyz/update-your-account-now-please-urgent\",^
   \"text\":\"You are under investigation. Stay on the line and do not disconnect.\"}"
```

Expect — tier **High**, score **0.523**, explanation (exact, SHAP-grounded):

> *Flagged as High risk because: message contains urgency and authority-impersonation
> language; link mimics a known brand domain; link uses a high-risk domain ending.
> Modules contributing: Module A (transaction–call), Module B (URL safety),
> Module C (message analysis, signature=fear_authority). Modules skipped: none.*

Say: *"Same transfer — Low alone, **High** correlated. No single channel was conclusive;
together they are. And it tells you which channels spoke, and which stayed silent.
That correlation layer **is** the project."* (Proven in code by
`tests/test_integration.py::test_combined_escalates_over_transaction_alone_thesis`.)

## 4:30 — Close (30s)

*"Rules today where data is missing, real classifiers the moment datasets arrive —
check `ml_status`. Limitations are on the table in `docs/LIMITATIONS.md`, including
that perfect Module A score being a synthetic-data artifact. Thank you — happy to take
the transaction-only path or the screenshot upload live."*

## If something fails (recovery lines)

| Failure | Line |
|---|---|
| Backend down (`health` fails) | *"The API isn't up — one moment."* Restart Terminal 1, re-run `curl …/health`. |
| Frontend blank | *"The API carries the demo."* Use the `curl` fallback for the current step. |
| Screenshot upload path | *"OCR needs the Tesseract binary; paste the text instead — same pipeline."* |
| Score differs slightly | *"Deterministic on the committed seed — retraining reproduces it. Scores, not vibes."* |
