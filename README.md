# TrueIntent — Multi-Channel Fraud Intent Verification System

> Banks verify *who* you are. Nobody verifies *why* you're sending the money. TrueIntent closes that gap.

TrueIntent helps a user (or analyst) check whether they are being manipulated into an authorized-but-fraudulent
transaction — e.g. "Digital Arrest" impersonation or fake stock-trading scams. It correlates **transaction context**
(an active phone call during a transfer) with **user-submitted evidence** (chat text/screenshots, suspicious links)
into **one explainable risk score** (Low / Medium / High / Critical) with a plain-language *why*, instead of
checking each signal in isolation. That correlation layer is the project's core contribution.

Full product spec: [`PROJECT_SPEC.md`](PROJECT_SPEC.md). Scoping decisions: [`docs/DECISIONS.md`](docs/DECISIONS.md).
Known limitations (read before evaluation): [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## Architecture

```text
                        ┌─────────────────────────┐
                        │      Frontend (UI)       │
                        │  React — 3 input forms   │
                        └────────────┬─────────────┘
                                     │ REST calls
                        ┌────────────▼─────────────┐
                        │     API Layer (FastAPI)   │
                        └──┬───────┬───────┬────────┘
                           │       │       │
              ┌────────────▼┐ ┌────▼────┐ ┌▼─────────────┐
              │ Module B     │ │ Module C │ │ Module A     │
              │ URL Checker  │ │ Msg/OCR  │ │ Txn+Call     │
              │ (rules + ML) │ │ Analyzer │ │ Correlation  │
              │              │ │ (OCR+NLP)│ │ (XGBoost)    │
              └────────────┬─┘ └────┬─────┘ └┬─────────────┘
                           │        │         │
                           └───┬────┴────┬────┘
                                ▼         ▼
                        ┌──────────────────────┐
                        │   Module D — Unified   │
                        │   Risk Scorer + SHAP   │
                        │   Explanation Engine   │
                        └───────────┬────────────┘
                                     ▼
                        ┌──────────────────────┐
                        │  Response: score +    │
                        │  plain-language why   │
                        └──────────────────────┘
```

| Module | What it does | Implementation status |
|---|---|---|
| **A — Transaction–Call Correlation** | XGBoost risk probability from amount, time, device, `is_active_call`, velocity | Trained on synthetic data (documented assumptions in `data/README.md`) |
| **B — URL Safety Checker** | Rule checks (IP host, typosquatting, TLD, obfuscation, length, + optional live page fetch) blended 50/50 with TF-IDF char n-gram + Logistic Regression when a dataset exists | **Rules-only** — `data/raw/module_b_urls.csv` pending |
| **C — Message/Screenshot Analyzer** | `fear_authority` vs `greed_opportunity` signatures; embedded URLs auto-checked by Module B; screenshot OCR via Tesseract | **Keyword baseline** — `sms_spam_collection.csv` + `signature_examples.csv` pending |
| **D — Unified Scorer + SHAP** | Renormalized weighted sum (A 0.45 / C 0.30 / B 0.25) → tier; SHAP-grounded plain-language explanation | Implemented; SHAP active for A, keyword-evidence fallback for C |
| **E — Web Portal** | Three calm, senior-friendly input views + shared results card | React + Tailwind, wired to the API |

---

## Project Structure

```text
├── backend/            # FastAPI app
│   ├── app/main.py         # Endpoints: /check-url, /check-message, /check-transaction, /check-combined
│   ├── app/schemas.py      # Pydantic v2 request/response models (mirror data/schema.md)
│   ├── requirements.txt
│   └── venv/               # Local virtualenv (created by setup, not committed)
├── frontend/           # React + Vite + Tailwind portal (Module E)
│   └── src/
│       ├── api.js              # API client (VITE_API_URL override supported)
│       ├── App.jsx             # Tab navigation across the three check views
│       └── components/         # LinkCheck, MessageCheck, TransactionCheck, Results, ui
├── ml/                 # ML pipelines
│   ├── predict_module_a.py # predict_module_a(transaction_dict) -> float
│   ├── predict_module_b.py # check_url(url) -> {score, reasons, ml_status}
│   ├── predict_module_c.py # analyze_message(text) -> {score, signature, reasons, ml_status}
│   ├── ocr_module_c.py     # extract_text_from_image() + analyze_image() (never false low-risk)
│   ├── predict_module_d.py # compute_unified_score(a, b, c) -> {tier, score, explanation, details}
│   ├── train_module_*.py   # Training entry points (A trains; B/C print DATASET PENDING without CSVs)
│   ├── generate_module_a_data.py  # Synthetic Module A data generator (seed 42, deterministic)
│   └── models/             # Trained artifacts (gitignored; only module_a.pkl exists locally)
├── data/
│   ├── raw/                # Datasets (gitignored) — only synthetic module_a_transactions.csv present
│   ├── README.md           # Per-module dataset status (present vs pending)
│   └── schema.md           # Canonical dataset schemas
├── tests/              # Pytest suite (43 passed, 2 skipped) + clearly-labeled synthetic OCR fixture
├── docs/               # decision_log.md (ADRs), DECISIONS.md, LIMITATIONS.md, coverage.md, architecture.md
├── setup.sh / setup.ps1
├── run-backend.sh / run-backend.ps1      # Backend on http://localhost:8000
├── run-frontend.sh / run-frontend.ps1   # Frontend on http://localhost:5173
└── Makefile
```

---

## Prerequisites

- **Python** 3.10+ · **Node.js** 18+ (npm 9+)
- **Tesseract OCR binary** (only needed for real screenshot OCR; text flows work without it):

| OS | Install |
|---|---|
| Ubuntu / Debian | `sudo apt-get install -y tesseract-ocr` |
| macOS (Homebrew) | `brew install tesseract` |
| Windows (Winget) | `winget install UB-Mannheim.TesseractOCR` |

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

Or: `make setup`. This creates `backend/venv`, installs Python deps, and runs `npm install` in `frontend/`.
These steps were exercised against this checkout (venv install + `npm install` + build all succeed).

### Train the models

Run from the **repo root** (scripts use relative `data/` / `ml/` paths):

```bash
# Module A: generates the synthetic dataset if missing, trains XGBoost, saves ml/models/module_a.pkl
.\backend\venv\Scripts\python.exe ml/train_module_a.py
```

Verified output on the committed seed: Precision **1.0000**, Recall **1.0000**, F1 **1.0000**, FPR **0.0000**
(60-sample holdout). These perfect scores are an artifact of the synthetic data's non-overlapping amount
ranges — see [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md); do not present them as real-world performance.

```bash
# Modules B/C: without their CSVs these print DATASET PENDING and exit (rules-only mode stays active)
.\backend\venv\Scripts\python.exe ml/train_module_b.py
.\backend\venv\Scripts\python.exe ml/train_module_c.py
```

To activate the ML classifiers, place CSVs in `data/raw/` per [`data/README.md`](data/README.md) and re-run:
- `module_b_urls.csv` with `url,label` columns (`label`: `phishing`/`legitimate`)
- `signature_examples.csv` with text + `signature` (`fear_authority`/`greed_opportunity`/`none`) columns,
  optionally plus `sms_spam_collection.csv` (ham rows supplement the `none` class)

---

## Running the app

Terminal 1 — backend (`http://localhost:8000`, interactive docs at `/docs`):

```powershell
.\run-backend.ps1
```

Terminal 2 — frontend (`http://localhost:5173`):

```powershell
.\run-frontend.ps1
```

To point the frontend at a non-default backend: `VITE_API_URL=http://localhost:8000 npm run dev`
(see `frontend/src/api.js`).

### API reference

| Method & path | Body | Returns |
|---|---|---|
| `POST /check-url` | `{"url": "..."}` | `{score, reasons, ml_status}` (Module B) |
| `POST /check-message` | form `text` **xor** file `image` | `{score, signature, reasons, ml_status, ocr_text?, ocr_status?}` (Module C) |
| `POST /check-transaction` | `{amount, timestamp?, device_id, is_active_call?, transaction_velocity?}` | `{score}` (Module A) |
| `POST /check-combined` | any subset of `{transaction, url, text}` | `{tier, score, explanation, details, modules}` (Module D) |

Errors are clear 4xx with human-readable messages (malformed URL → 422, missing input → 400/422,
unreadable image → 400, OCR engine missing → 503) — never raw stack traces. The API skips live page
fetching (`fetch_live_page=False`) for deterministic, offline-safe responses.

---

## Running the tests

Canonical command (uses the project venv; also `make test`):

```bash
cd backend
.\venv\Scripts\pytest ..\tests\
```

Verified: **43 passed, 2 skipped** (skips are the real-screenshot evidence tests awaiting user-provided
screenshots / a Tesseract binary). Full coverage report: [`docs/coverage.md`](docs/coverage.md) —
53% overall, ~70% on serving+inference code (one-shot training scripts excluded).

---

## Demo walkthrough (verified outputs)

Backend running on `:8000`, frontend on `:5173`.

**1. Check a link** — paste `http://192.168.1.1/verify-account` → score **0.6** with reasons
"Insecure protocol…" and "Host is a raw IP address (192.168.1.1)…".

**2. Check a message** — paste `You are under investigation. Stay on the line and do not disconnect.`
→ signature `fear_authority`, combined tier **Critical (0.9)**. Try appending
`http://192.168.1.1/verify-account` to see Module B evidence folded into the message result.

**3. Simulate a transaction** — amount `45000`, active call **on** → score **0.9889**; the same form with
`500`, call **off** → **0.0066**. Then submit all three together via `/check-combined` to see Module D
escalate a legitimate-looking transfer once coercion evidence is correlated
(covered by `tests/test_integration.py`).

---

## Data & privacy

- Only **synthetic** transaction data exists in-repo; `data/raw/*` and `*.pkl` artifacts are gitignored,
  so no real PII or raw evidence can leak into version control.
- The OCR failure contract guarantees blurry/unreadable screenshots return
  `ocr_status: insufficient_text` with a "try a clearer screenshot" message — never a false low-risk score.
- Test images: only a clearly-labeled **synthetic** fixture (`tests/data/synthetic_chat_fear_authority.png`);
  no fabricated evidence is presented as real (see `tests/test_module_c_ocr.py`).

## Docs index

- [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — full product specification
- [`docs/decision_log.md`](docs/decision_log.md) — ADRs 001–005
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — scoping decisions made during the build
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — limitations (spec §12 + discovered issues)
- [`docs/coverage.md`](docs/coverage.md) — test coverage report
- [`docs/architecture.md`](docs/architecture.md) — system architecture
- [`data/README.md`](data/README.md) / [`data/schema.md`](data/schema.md) — dataset status & schemas
