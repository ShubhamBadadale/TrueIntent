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
| **A — Transaction–Call Correlation** | XGBoost risk probability from amount, time, device, `is_active_call`, velocity | Hybrid IEEE-CIS + synthetic call/device flags; chronological F1 0.1562, recall delta +11.39 pp. Not real-world performance; see `data/DATASHEET.md` |
| **B — URL Safety Checker** | Rule checks (IP host, typosquatting, TLD, obfuscation, length, + optional live page fetch) blended 50/50 with TF-IDF char n-gram + Logistic Regression | **Active** — trained on 11,427 real historical URL rows; classifier holdout F1 0.9101 (not current real-world performance). See `data/README.md`. |
| **C - Message/Screenshot Analyzer** | Trained TF-IDF + Logistic Regression with existing keyword safeguards and URL/OCR paths | **Active, fear unvalidated**: 5 cited fear excerpts, OOF recall 0/5. See `data/MODULE_C_DATASHEET.md`. |
| **D - Unified Scorer + SHAP** | Learned three-score logistic policy; log-odds contributions and module explanations | Active on synthetic joint labels, not real incidents. [Evaluation](data/MODULE_D_DATASHEET.md) |
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
│   ├── generate_module_a_data.py  # IEEE-CIS ingestion + simulated telemetry (seed 42)
│   └── models/             # Trained artifacts (gitignored; only module_a.pkl exists locally)
├── data/
│   ├── raw/                # Datasets (gitignored); Module B now includes real historical URLs
│   ├── README.md           # Per-module dataset status (present vs pending)
│   └── schema.md           # Canonical dataset schemas
├── tests/              # Pytest suite (81 passed, 2 skipped) + clearly-labeled synthetic OCR fixture
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
# Module A: requires local IEEE-CIS data; generates hybrid features then trains
.\backend\venv\Scripts\python.exe ml/generate_module_a_data.py
.\backend\venv\Scripts\python.exe ml/train_module_a.py
```

Phase 2 chronological holdout: precision **0.0881**, recall **0.6863**, F1 **0.1562**,
FPR **0.2531**. Removing synthetic telemetry yields recall **0.5723** (delta **+11.39 pp**).
These are assumption-dependent hybrid-data results, not real-world performance.
See [`data/DATASHEET.md`](data/DATASHEET.md) for the full comparison and known limitations.

```bash
# Modules B/C: without their CSVs these print DATASET PENDING and exit (rules-only mode stays active)
.\backend\venv\Scripts\python.exe ml/train_module_b.py
.\backend\venv\Scripts\python.exe ml/train_module_c.py
```

To activate the ML classifiers, place CSVs in `data/raw/` per [`data/README.md`](data/README.md) and re-run:
- Module B: run `python ml/generate_module_b_data.py`, then `python ml/train_module_b.py`.
  This downloads the public Kaggle v2 dataset and writes `module_b_urls.csv` with `url,label`
  (`phishing`/`legitimate`). See [`data/README.md`](data/README.md) for offline ingestion,
  attribution, metrics and limitations. Restart the backend after retraining.
- Module C: run `.\backend\venv\Scripts\python.exe ml/generate_module_c_data.py`, then
  `.\backend\venv\Scripts\python.exe ml/train_module_c.py`. The assembled CSV includes
  source metadata; see [Module C datasheet](data/MODULE_C_DATASHEET.md).

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
| `POST /check-transaction` | `{amount, timestamp?, device_id, is_active_call?, transaction_velocity?, call_telemetry?}` | `{score}` (Module A) |
| `POST /check-combined` | any subset of `{transaction, url, text}` | `{tier, score, explanation, details, modules}` (Module D) |

Errors are clear 4xx with human-readable messages (malformed URL → 422, missing input → 400/422,
unreadable image → 400, OCR engine missing → 503) — never raw stack traces. The API skips live page
fetching (`fetch_live_page=False`) for deterministic, offline-safe responses.

### Docker packaging (legacy, not revalidated)

The old Dockerfile assumes build-time synthetic training and excludes local artifacts.
It requires updating before use with the current datasets; use native setup for these phases.
The historical command is:

```bash
docker compose up --build
```

- Frontend demo: `http://localhost:5173` · Backend API/docs: `http://localhost:8000` (`/docs`)
- Module A build-time training now requires authorized IEEE-CIS data (or generated data plus metadata).
  The backend image installs the Tesseract binary and retrains Module A at build
  time; a fresh clone without the authorized data can no longer train Module A.
- Stop with `docker compose down -v`. To target a remote backend, rebuild the frontend with
  `docker compose build --build-arg VITE_API_URL=http://<host>:8000`.

---

## Running the tests

Canonical command (uses the project venv; also `make test`):

```bash
cd backend
.\venv\Scripts\pytest ..\tests\
```

Verified: **81 passed, 2 skipped** (skips are the real-screenshot evidence tests awaiting user-provided
screenshots / a Tesseract binary). Historical coverage report (not remeasured for these upgrades): [`docs/coverage.md`](docs/coverage.md) —
53% overall, ~70% on serving+inference code (one-shot training scripts excluded).

---

## Demo walkthrough (verified outputs)

Backend running on `:8000`, frontend on `:5173`.

**1. Check a link** - paste `http://192.168.1.1/verify-account` and inspect the
blended classifier/rule score and reasons.

**2. Check a message** - paste `You are under investigation. Stay on the line and do not disconnect.`
Keyword safeguards can flag fear language; the trained fear class remains unvalidated.

**3. Check a transaction** - use the manual web form or the
[Android companion](docs/ANDROID_COMPANION.md). Scores depend on the current artifact;
old synthetic amount-based demo scores are obsolete. Combined tiers follow the
learned synthetic policy described in the [D datasheet](data/MODULE_D_DATASHEET.md).

---

## Data & privacy

- Module B uses real, historical public URL data; Module A uses **real IEEE-CIS amounts/labels with synthetic call/device flags**.
  `data/raw/*` and `*.pkl` artifacts are gitignored and must be regenerated on a fresh checkout.
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
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — 5-minute live demo script (evaluation day)

> **Spec §13 deliverable mapping:** working prototype (this repo, Docker included), GitHub repo +
> setup instructions (here), test suite with coverage (above), demo script (`docs/DEMO_SCRIPT.md`).
> The prose final report (related work, full results narrative) is a separate written submission —
> its technical chapters already exist as `docs/DECISIONS.md`, `docs/LIMITATIONS.md`,
> `docs/coverage.md`, and `docs/architecture.md`.

### Module C Phase 4 reproduction and limits

Run `.\backend\venv\Scripts\python.exe ml/generate_module_c_data.py`, then
`.\backend\venv\Scripts\python.exe ml/train_module_c.py`. Restart the backend.
This uses source ZIPs and writes the assembled `text,signature` CSV; the trainer
no longer adds an extra ham sample from a separate CSV. Keyword safeguards remain.
Fear/authority recall is **0/5** out of fold. Greed and ham F1 are **0.9918/0.9937**,
with weak labels and severe source/style confounding; these are not real-world
performance estimates. [Data and per-class evaluation](data/MODULE_C_DATASHEET.md).

### Completed fusion and phone-signal implementation

Module D reproduction and coefficients: [datasheet](data/MODULE_D_DATASHEET.md).
Android setup, payload, scope and verification: [companion guide](docs/ANDROID_COMPANION.md).
Restart the backend to load the new code. Manual transaction input still works.
