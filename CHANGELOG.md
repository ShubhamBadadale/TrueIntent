# TrueIntent Changelog

Build history in the order work landed. Iteration numbers are given only where
they are stated in the repo or review record (Iterations 3, 7, 9); other phases
are labeled by what they built.

## Scaffold & Module A — Transaction–Call Correlation Engine
- Monorepo layout (`backend/`, `frontend/`, `ml/`, `data/`, `tests/`, `docs/`).
- Synthetic Module A dataset generator (seed 42) with documented APP-fraud
  assumptions; XGBoost training script (`ml/train_module_a.py`); inference
  (`predict_module_a`) with timestamp/device feature engineering (ADR-003).

## Iteration 3 — Dataset schemas & Module B URL safety checker
- Canonical dataset schemas (`data/schema.md`) for Modules A/B/C.
- `check_url()` rule engine: URL length, IP host, suspicious characters,
  brand-typosquatting similarity, high-risk TLDs, optional live page fetch;
  TF-IDF + Logistic Regression hook that stays rules-only until
  `data/raw/module_b_urls.csv` is provided (ADR-004).

## Module C — Message/screenshot text analysis
- `analyze_message()` with `fear_authority` / `greed_opportunity` / `none`
  signatures over a documented keyword baseline (TF-IDF hook pending the SMS /
  signature datasets); embedded URLs auto-checked by Module B and folded into
  the score; pytest coverage for both signatures plus clean/edge cases.

## Iteration 7 — Screenshot OCR extension
- `extract_text_from_image()` (pytesseract) + `analyze_image()` wired into the
  text pipeline, with a no-false-low-risk failure contract (`ocr_status`:
  `ok` / `insufficient_text` / `ocr_unavailable` / `invalid_image`).
- OCR tests use mocks, a blank control image, and one user-approved,
  clearly labeled synthetic fixture — no fabricated evidence.

## Module D — Unified risk scorer (correlation layer)
- `compute_unified_score()` with named, renormalized weights
  (A 0.45 / C 0.30 / B 0.25), Low/Medium/High/Critical tiers, honest
  contributing-vs-skipped reporting, and SHAP grounding (TreeExplainer for A,
  exact linear-SHAP tokens for C) with labeled fallbacks (ADR-005).

## Iteration 9 — FastAPI backend
- `backend/app` with Pydantic v2 schemas plus four endpoints (`/check-url`,
  `/check-message`, `/check-transaction`, `/check-combined`), 4xx-first error
  handling, local-origin CORS, and 13 TestClient tests.

## Module E — React portal
- Three calm, senior-friendly input views (link / message-or-screenshot /
  transaction scenario) sharing one tier-colored results card with loading and
  server-unreachable states, wired to the backend endpoints.

## Integration tests & coverage
- `tests/test_integration.py`: URL-flow coherence, Module C→B folding, the
  Module D escalation proof (the correlation-layer thesis test), and
  frontend→backend route wiring. Suite: 43 passed, 2 skipped
  (`docs/coverage.md`: 53% overall, ~70% on serving/inference code).

## Evaluation & reproducibility hardening
- Full `README.md` (verified setup/demo), `docs/DECISIONS.md` (11 scoping
  decisions), `docs/LIMITATIONS.md` (spec §12 + observed issues), data-doc
  reconciliation, pinned backend (`==`) and frontend (exact) dependencies.
- Docker: `backend/Dockerfile` (retrains Module A deterministically at build),
  `frontend/Dockerfile`, `docker-compose.yml` (`up` serves :5173 → :8000).
