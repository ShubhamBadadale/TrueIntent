# TrueIntent — Multi-Channel Fraud Intent Verification System

> Banks verify *who* you are. Nobody verifies *why* you're sending the money. TrueIntent closes that gap.

TrueIntent helps a user (or analyst) decide whether they are being manipulated into a
fraudulent transaction — e.g. "Digital Arrest" impersonation or a fake stock-trading group. It
combines **user-submitted evidence** (chat text, screenshots, suspicious links) with an optional
**user-reported call state** into **one explainable risk index** (Low / Medium / High / Critical)
with a plain-language *why*, instead of checking each signal in isolation. That correlation layer is
the project's contribution.

**Module A is not a transaction risk engine.** It is an amount-only research benchmark over the
IEEE-CIS card-fraud corpus in its original source units. Real INR transaction assessment and any
transaction/call-context fusion are disabled, and the API refuses them explicitly rather than
substituting a plausible score. See [Module A correctness](docs/MODULE_A_CORRECTNESS.md) and
[Limitations](docs/LIMITATIONS.md).

Full product spec: [`PROJECT_SPEC.md`](PROJECT_SPEC.md). Scoping decisions:
[`docs/DECISIONS.md`](docs/DECISIONS.md) and the ADRs in [`docs/decision_log.md`](docs/decision_log.md).
Repository audit: [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md).

---

## Architecture

```text
              +-------------------------+
              |      Frontend (UI)      |
              |  React — 4 input views  |
              +------------+------------+
                           | REST calls
              +------------v-------------+
              |     API Layer (FastAPI)  |
              +---+---------+--------+---+
                  |         |        |
        +---------v--+ +----v-----+ +-v----------------+
        | Module B   | | Module C | | Module A         |
        | URL Checker| | Msg/OCR  | | Amount-only      |
        | (rules+ML) | | (OCR+NLP)| | IEEE-CIS bench   |
        +---------+--+ +----+-----+ +----+-----------+
                  |         |            |
                  |         |     (excluded from fusion)
                  +----+----+----+
                       |         |
              +--------v---------v--------+
              |  Module D - Unified Risk   |
              |  Scorer + Explanation       |
              +-------------+--------------+
                            |
              +-------------v--------------+
              |  Response: risk index +    |
              |  plain-language why        |
              +----------------------------+
```

| Module | What it does | Implementation status |
|---|---|---|
| **A — Amount-only benchmark** | Source-unit amount XGBoost contract; no INR, clock, device or call inference | **No artifact in this checkout**; transaction fusion disabled. [Correctness](docs/MODULE_A_CORRECTNESS.md) |
| **B — URL Safety Checker** | Offline rules blended 50/50 with character TF-IDF + logistic regression; never fetches a page | Trained on real historical URLs (May 2020), evaluated with a registered-domain-disjoint split. [Evaluation](docs/MODULE_B_EVALUATION.md) |
| **C — Message/Screenshot Analyzer** | 10-class intent classifier + OCR + embedded-URL analysis; keyword lists are evidence-only | Thin real-language support; most classes rest on authored examples. [Evaluation](docs/MODULE_C_INTENT_EVALUATION.md) |
| **D — Unified Scorer** | Availability-aware logistic policy with channel interactions and plain-language factors | Synthetic-policy evaluation only, not real-world fraud validation. [Evaluation](docs/MODULE_D_FUSION_EVALUATION.md) |
| **E — Web Portal** | Combined Fraud Analysis plus three single-channel views | Presents every output as an uncalibrated Risk Index; unavailable evidence is stated explicitly |

---

## Project structure

```text
├── backend/            # FastAPI app
│   ├── __main__.py         # `python -m backend` entry point (the documented start command)
│   ├── app/main.py         # app factory: middleware, CORS, exception handlers, routers
│   ├── app/config.py       # TRUEINTENT_* environment configuration
│   ├── app/errors.py       # stable error codes shared by both route generations
│   ├── app/services.py     # analysis logic shared by v1 and legacy routes
│   ├── app/validation.py   # URL limits, MIME magic-byte checks, bounded reads
│   ├── app/v1_routes.py    # /api/v1/* envelope contract
│   ├── app/legacy_routes.py# /check-* frozen compatibility routes
│   ├── app/health.py       # /, /health, /ready
│   ├── app/diagnostics.py  # readiness probes
│   ├── app/schemas.py      # legacy Pydantic models (unchanged shape)
│   ├── app/v1_schemas.py   # v1 request/response models
│   ├── requirements.txt    # pinned runtime deps
│   └── requirements-dev.txt# pinned test deps (pytest, pytest-cov, httpx)
├── frontend/           # React + Vite + Tailwind portal (Module E)
│   ├── src/api.js              # API client (VITE_API_URL override) + shared input limits
│   ├── src/combinedAnalysis.js # combined-flow input preparation
│   ├── src/App.jsx             # tab navigation across the four views
│   ├── src/components/         # LinkCheck, MessageCheck, TransactionCheck, CombinedCheck, Results
│   └── tests/                  # node --test regressions (render components, mock fetch)
├── ml/                 # ML pipelines
│   ├── features_module_{a,b,c,d}.py  # shared feature contracts (single source of truth)
│   ├── predict_module_{a,b,c,d}.py    # serving boundaries
│   ├── ocr_module_c.py                # OCR extension for Module C
│   ├── model_loading.py               # cached, trust-checked artifact loader
│   ├── train_module_{b,c,d}.py        # training entry points
│   └── models/                        # trained artifacts (gitignored, *.pkl)
├── data/               # dataset status, schemas and datasheets
├── android/            # optional call-signal companion app
├── tests/              # pytest suite
├── docs/               # audit, ADRs, decisions, limitations, evaluations, demo script
├── setup.sh / setup.ps1, run-backend.*, run-frontend.*, Makefile
├── .env.example        # optional configuration (no secrets; app runs with no config)
└── pytest.ini
```

The canonical Python environment is **`.venv/` at the repo root**. There is no `backend/venv`.

---

## Prerequisites

- **Python** 3.11+ (pinned artifact versions were verified on CPython 3.11)
- **Node.js** 20.19+ or 22.12+ (Vite 8 requires it; `npm test` uses `node --test` with `t.mock`)
- **Tesseract OCR binary** — only needed for screenshot OCR. Text flows work without it.

| OS | Install |
|---|---|
| Ubuntu / Debian | `sudo apt-get install -y tesseract-ocr` |
| macOS (Homebrew) | `brew install tesseract` |
| Windows (Winget) | `winget install UB-Mannheim.TesseractOCR` |

If Tesseract is not on `PATH` (common on Windows), set `TESSERACT_CMD` — see
[`.env.example`](.env.example).

---

## Setup (from a clean clone)

```bash
git clone https://github.com/ShubhamBadadale/TrueIntent.git
cd TrueIntent
```

Windows (PowerShell):

```powershell
.\setup.ps1
```

Linux / macOS:

```bash
chmod +x setup.sh run-backend.sh run-frontend.sh
./setup.sh
```

`make setup` does the same. This creates `.venv`, installs
`backend/requirements.txt` + `backend/requirements-dev.txt`, and runs `npm install` in
`frontend/`. Verified from a clean clone: a brand-new virtualenv installs the pinned
requirements and the full suite passes.

---

## Running the app

Terminal 1 — backend (`http://localhost:8000`, interactive docs at `/docs`):

```powershell
.\run-backend.ps1
```

which runs the single documented command from the repo root:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8000
```

Terminal 2 — frontend (`http://localhost:5173`):

```powershell
.\run-frontend.ps1
```

To point the frontend at a non-default backend:
`VITE_API_URL=http://localhost:8000 npm run dev` (see `frontend/src/api.js`).

### API reference

Two route generations share one service layer. New clients should use `/api/v1/*`, which returns
the envelope `{"success", "data", "meta": {"request_id", "api_version"}}` on success and
`{"success": false, "error": {"code", "message", "module", "details"}}` on failure. The
`/check-*` routes return the original flat bodies and are frozen. Full contract:
[`docs/API_V1.md`](docs/API_V1.md).

| Method & path | Body | Returns |
|---|---|---|
| `GET /health` | — | `{"status":"ok"}` — process liveness only, not model availability |
| `GET /ready` | — | readiness with per-component diagnostics (200, or 503 when broken) |
| `POST /api/v1/analyze/url` | `{"url": "..."}` | `{score, risk_index, reasons, ml_status}` (Module B) |
| `POST /api/v1/analyze/message` | `{"text": "..."}` (JSON, no multipart) | `{score, risk_index, signature, reasons, ml_status, text_assessed, intent?, …}` (Module C) |
| `POST /api/v1/analyze/image` | file `image` | message shape plus `ocr_text?`, `ocr_status?` (Module C + OCR) |
| `POST /api/v1/analyze/combined` | any subset of `{url, text, active_call?}` | `{tier, score, risk_index, explanation, details, modules}` (Module D) |
| `POST /api/v1/module-a/benchmark` | `{amount, amount_unit, …}` (`amount_unit` required) | `{score, analysis_scope, explanation}` (Module A benchmark) |
| `GET /api/v1/module-a/contract` | — | the versioned Module A feature contract |
| `POST /check-url` | `{"url": "..."}` | `{score, reasons, ml_status}` (Module B, legacy) |
| `POST /check-message` | form `text` **xor** file `image` | message shape (Module C, legacy) |
| `POST /check-transaction` | `{amount, amount_unit, …}` (`INR` default) | `{score, analysis_scope, explanation}` (Module A, legacy) |
| `POST /check-combined` | any subset of `{transaction, url, text, active_call?}` | `{tier, score, explanation, details, modules}` (Module D, legacy) |

Notes that matter for callers:

- `/check-transaction` requires the explicit `amount_unit: "ieee_cis_source"` opt-in. Omitting it
  leaves the `INR` default and returns **422** — the system will not relabel a rupee amount as
  dataset units. With the correct unit but no trained artifact it returns **503**, never a
  substituted score.
- `/check-combined` refuses a `transaction` field with **422** and an explicit explanation; the
  field exists only so that refusal is a clear message rather than a silent drop.
- `timestamp`, `device_id`, `is_active_call`, `transaction_velocity` and `call_telemetry` on
  `/check-transaction` are validated legacy metadata. They are echoed for caller compatibility and
  are **never** model features or fusion evidence.
- Errors are clear 4xx/5xx with human-readable, display-safe messages (malformed URL → 422,
  missing input → 400/422, unreadable image → 400, oversized upload → 413, unsupported type →
  415, OCR engine missing → 503, model unavailable → 503) — never raw stack traces, paths or
  environment values. Every response carries an `X-Request-ID` that matches `meta.request_id`,
  so a failure can be traced in the server log. The API never fetches live pages
  (`fetch_live_page=False`), so responses are deterministic and egress-free.
- Uploads are verified, not trusted: the declared MIME type, filename extension and actual magic
  bytes must agree, bodies are read in bounded chunks behind a whole-request size gate, and
  images are capped at 10 MB / 10 megapixels. CORS origins, log format and every limit are
  configurable through `TRUEINTENT_*` environment variables — see [`.env.example`](.env.example).

### Docker packaging (local demo)

The build installs dependencies and OCR but never trains models. Compose mounts
`ml/models` read-only, so supply trusted artifacts produced in this project's pinned Python 3.11
environment. Missing models keep the API's explicit unavailable/fallback behaviour.

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173` · Backend API/docs: `http://localhost:8000` (`/docs`)
- Both published ports bind to localhost. Stop with `docker compose down -v`.
- To target a remote backend, rebuild the frontend with
  `docker compose build --build-arg VITE_API_URL=http://<host>:8000`.
- Docker was unavailable during this audit, so container startup is not verified locally.

---

## Training the models

Run from the **repo root**.

```bash
# Module B: needs data/raw/module_b_urls.csv (see data/README.md for the verified source)
.\.venv\Scripts\python.exe ml\train_module_b.py

# Module C: needs data/raw/signature_examples.csv, which requires network source downloads
.\.venv\Scripts\python.exe ml\train_module_c.py

# Module D: fully self-contained synthetic interaction-policy simulation
.\.venv\Scripts\python.exe ml\train_module_d.py
```

Module D trains from a clean checkout. Module B prints `DATASET PENDING` until its CSV exists.
Module C likewise. **Module A cannot be trained here** — it requires authorized IEEE-CIS
`train_transaction.csv`, and `ml/train_module_a_data.py` stops with an explicit
`FileNotFoundError` rather than fabricating a substitute.

Restart the backend after retraining to clear its in-memory model caches.

### Current measured results

| Module | Split | Precision | Recall | F1 | FPR |
|---|---|---:|---:|---:|---:|
| B (classifier only, not the blend) | random 80/20 | 0.9173 | 0.9020 | 0.9096 | 0.0814 |
| B (classifier only) | registered-domain-disjoint | 0.8624 | 0.9281 | 0.8941 | 0.1479 |
| C (10 intents, `word_char`) | 5 grouped OOF folds | — | — | macro 0.3264 | — |
| D (serving policy, A+B+C) | 200 synthetic test scenarios | 0.8846 | 0.7731 | 0.8251 | — |
| D (serving policy, B+C) | 200 synthetic test scenarios | 0.7500 | 0.6303 | 0.6849 | — |
| A | — | **not measured** | **not measured** | **not measured** | — |

These are research numbers on historical or synthetic data. They are **not** real-world fraud
performance. Full tables and caveats: [Module B](docs/MODULE_B_EVALUATION.md),
[Module C](docs/MODULE_C_INTENT_EVALUATION.md), [Module D](docs/MODULE_D_FUSION_EVALUATION.md),
[Module A](docs/MODULE_A_CORRECTNESS.md).

---

## Running the tests

```bash
.\.venv\Scripts\python.exe -m pytest
```

or `make test`, or `make test-cov` for a coverage report.

**Current result: 179 passed, 2 skipped** (the two skips need user-supplied real screenshots
and a Tesseract binary). Coverage measured on this commit: **81% overall**, **84%** across
serving + inference code — see [`docs/coverage.md`](docs/coverage.md). The v1 envelope, every
error class, request-ID propagation, CORS behaviour, upload limits and readiness are all asserted
through the TestClient in `tests/backend/test_api_v1.py`.

Frontend regressions:

```bash
cd frontend && npm test    # 14 passed
```

Tests that need a trained Module B/C artifact skip honestly when the artifact is absent
(`data/raw/` and `*.pkl` are gitignored) rather than failing on a clean clone.

---

## Demo walkthrough (verified outputs)

Backend on `:8000`, frontend on `:5173`. Reproduced against the current build; a longer script is
in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

1. **Check a link** — `http://192.168.1.1/verify-account` → Risk Index **79/100**
   (`score 0.7944`), reasons: insecure protocol, raw IP host. `https://www.google.com/search?q=test`
   → **4/100** (`0.0357`) with no reasons.
2. **Check a message** — `You are under investigation for money laundering. Stay on the line and do
   not disconnect.` → `score 0.707`, signature `fear_authority`, intent `digital_arrest`.
3. **Combine evidence** — safe URL + ordinary lunch text → **Low, 0.0938**. The same submission
   with a raw-IP link and a coercion message plus a reported active call → **High, 0.5086**, with
   the explanation naming the contributing and skipped modules.
4. **Transaction benchmark** — the Transaction view accepts an IEEE-CIS source-unit amount and
   labels the result a benchmark, never a transfer-risk tier. Without a trained artifact the API
   returns 503 and says so.

---

## Data & privacy

- `data/raw/*` and `*.pkl` artifacts are gitignored and must be regenerated on a fresh checkout.
  Module B uses real historical public URLs; Module A would use real IEEE-CIS amounts.
- Nothing is persisted server-side: no database, no raw screenshots, no transaction records.
- The OCR failure contract guarantees blurry or unreadable screenshots return
  `ocr_status: insufficient_text` with a "try a clearer screenshot" message — never a false
  low-risk score.
- Test images: only a clearly-labeled **synthetic** fixture
  (`tests/data/synthetic_chat_fear_authority.png`). No fabricated evidence is presented as real.

## Docs index

| Document | Contents |
|---|---|
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | Full product specification |
| [`docs/API_V1.md`](docs/API_V1.md) | Versioned API contract for web and future mobile clients |
| [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md) | Repository audit: issues found, fixed, remaining |
| [`docs/decision_log.md`](docs/decision_log.md) | Architecture decision records (ADR-001…006) |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Build-time scoping decisions (D-01…D-12) |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | Known limitations (spec §12 + observed issues) |
| [`docs/coverage.md`](docs/coverage.md) | Test coverage report |
| [`docs/architecture.md`](docs/architecture.md) | System architecture |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | 5-minute live demo script |
| [`docs/ANDROID_COMPANION.md`](docs/ANDROID_COMPANION.md) | Optional call-signal companion app |
| [`data/README.md`](data/README.md) / [`data/schema.md`](data/schema.md) | Dataset status and schemas |
| [`EXPLAINER.md`](EXPLAINER.md) | Long-form module-by-module walkthrough |

> **Spec §13 deliverable mapping:** working prototype (this repo, Docker included), GitHub repo
> plus setup instructions, test suite with coverage, and a demo script. The prose final report
> (related work, full results narrative) is a separate written submission whose technical chapters
> already exist as `docs/DECISIONS.md`, `docs/LIMITATIONS.md`, `docs/coverage.md` and
> `docs/architecture.md`.