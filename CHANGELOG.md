# TrueIntent Changelog

Build history in the order work landed. Iteration numbers are given only where they are stated in
the repo or review record; other phases are labeled by what they built. Superseded entries are kept
and annotated rather than rewritten, so the trail stays auditable.

## Scaffold & Module A — Transaction–Call Correlation Engine
- Monorepo layout (`backend/`, `frontend/`, `ml/`, `data/`, `tests/`, `docs/`).
- ~~Synthetic Module A dataset generator (seed 42) with documented APP-fraud assumptions~~
  — **superseded**, see ADR-006 and the Module A correctness update.

## Iteration 3 — Dataset schemas & Module B URL safety checker
- Canonical dataset schemas (`data/schema.md`).
- `check_url()` rule engine: URL length, IP host, obfuscation characters, brand-typosquatting
  similarity, high-risk TLDs; TF-IDF + logistic regression blended 50/50 with the rules
  (ADR-004).

## Module C — Message/screenshot text analysis
- `analyze_message()` with `fear_authority` / `greed_opportunity` / `none` psychology signatures;
  embedded URLs auto-checked by Module B and folded into the score.
- ~~Documented keyword baseline~~ — **superseded**: keyword lists are now ablation-only evidence
  and never override the classifier.

## Iteration 7 — Screenshot OCR extension
- `extract_text_from_image()` (pytesseract) + `analyze_image()` wired into the text pipeline, with
  a no-false-low-risk failure contract (`ocr_status`: `ok` / `insufficient_text` /
  `ocr_unavailable` / `invalid_image`).
- OCR tests use mocks, a blank control image, and one user-approved, clearly labeled synthetic
  fixture — no fabricated evidence.

## Module D — Unified risk scorer (correlation layer)
- `compute_unified_score()` with Low/Medium/High/Critical tiers, honest contributing-vs-skipped
  reporting, coefficient-level attribution, and a renormalized fixed-weight fallback when no
  artifact exists (ADR-005, amended to v2 in ADR-005).

## Iteration 9 — FastAPI backend
- `backend/app` with Pydantic v2 schemas plus `/check-url`, `/check-message`,
  `/check-transaction`, `/check-combined`, 4xx/5xx-first error handling, and local-origin CORS.

## Module E — React portal
- Four calm, senior-friendly views (combined / link / message-or-screenshot / transaction
  benchmark) sharing one tier-coloured results card with loading and server-unreachable states.

## Integration tests & coverage
- `tests/test_integration.py`: URL-flow coherence, Module C→B folding, refusal of obsolete
  transaction fusion, and frontend→backend route wiring.

## Evaluation & reproducibility hardening
- Full `README.md`, `docs/DECISIONS.md`, `docs/LIMITATIONS.md`, data-doc reconciliation, pinned
  backend (`==`) and frontend (exact) dependencies.
- Docker: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`.
  ~~Retrains Module A deterministically at build~~ — **superseded**; builds train nothing and mount
  `ml/models` read-only.

## Correctness pass — Module A becomes an amount-only benchmark
- Replaced the six-feature contract with a single `amount` feature in the explicit IEEE-CIS source
  unit; versioned `FEATURE_CONTRACT` enforced by `validate_artifact()`; legacy artifacts rejected.
- Deleted the synthetic telemetry generator and `ml/module_a_priors.json`.
- `/check-transaction` now requires an explicit `amount_unit` opt-in (422 otherwise), returns 503
  when no artifact exists, and reports `analysis_scope` on success.
- Transaction-bearing `/check-combined` requests are refused; `compute_unified_score()` rejects
  transaction-context dictionaries.
- ADR-003 marked superseded; ADR-006 added.

## Module C intent-v2 & Module D interaction policy
- Module C: ten-intent model with explicit provenance, grouped OOF evaluation and Hindi/Hinglish
  seeds; keyword rules retained only as evidence. The two-signature compatibility model is kept for
  explanation wording.
- Module D: fourteen-feature availability-aware logistic policy with presence flags and four
  cross-channel interactions; legacy three-score artifacts stay readable.
- `data/MODULE_D_DATASHEET.md`, `docs/MODULE_C_INTENT_EVALUATION.md`,
  `docs/MODULE_D_FUSION_EVALUATION.md`.

## Combined Fraud Analysis view
- Added the combined-evidence tab to the portal: screenshot OCR feeding `/check-combined`, message
  and URL folding, honest "unassessed" state when only context is supplied.
- Frontend SSR regressions under `node --test`.

## Backend hardening (v1 API)
- Versioned `/api/v1/*` contract with success/error envelopes, stable error codes, request IDs
  (`X-Request-ID` echoed and logged), and a mobile integration reference (`docs/API_V1.md`).
- One service layer (`backend/app/services.py`) serves both the v1 routes and the frozen
  `/check-*` compatibility routes, whose bodies and error shapes are byte-identical.
- Hardening: env-driven config (`TRUEINTENT_*`, see `.env.example`), structured logging, MIME
  magic-byte verification, bounded chunked upload reads behind a request-size gate, explicit
  threadpool offload on every v1 handler, `/health` + `/ready` with honest component diagnostics,
  CORS origins from the environment, `python -m backend` as the single start command, and a
  `ModuleDUnavailableError` that maps corrupt fusion artifacts to 503.
- OCR failure reasons no longer interpolate upstream exception text; the exception type is logged
  server-side instead. `TESSERACT_LANG` is now honoured (it was documented but unimplemented).
- Suite: 206 passed, 2 skipped; coverage 81% overall, 84% on serving + inference code.

## Repository audit (previous)
- Removed unreachable and duplicated code: `generate_legacy_module_d_data`,
  `train_legacy_module_d`, `train_legacy_module_c`, `is_ip_address`, the unreachable
  `WEIGHT_LOGIN_FORM_PRESENT` login-form branch, and the synthetic signature-example generator that
  could have destroyed Module C provenance.
- Repaired broken direct-script imports so `python ml/predict_module_c.py` and
  `python ml/predict_module_d.py` work.
- Unified the FastAPI app on a single module identity (`backend.app.main`) so tests and coverage no
  longer see two copies of the app.
- Unified the virtualenv on `.venv/` at the repo root; rewrote `Makefile`, `setup.*`,
  `run-backend.*`, `run-frontend.*` and made `setup.ps1` locate Python when it is not on `PATH`.
- Split `backend/requirements.txt` (runtime) from the new `backend/requirements-dev.txt`; added
  `pytest.ini` and `.env.example`; added `TESSERACT_CMD` support for OCR.
- Hardened the Android companion's payload to the benchmark contract so it is no longer guaranteed
  to receive a 422.
- Rewrote every documentation claim that contradicted the code, and re-measured the demo outputs
  against a running backend.
- Full report: [`docs/AUDIT_REPORT.md`](docs/AUDIT_REPORT.md).

## Module D rebuild — central fusion layer (v3)
- Standardized module-result contract (`{module, assessed, score, confidence, risk_level, evidence, model_version, abstention_reason}`); unavailable modules keep `score: null` and are never fused as zero.
- Combined result now carries overall risk score + risk level, analyzed/contributing/unavailable modules, evidence, warnings, fusion version, limitations and a recommended action; output is worded as a risk score, never a fraud probability.
- Thresholds, fallback weights, levels and limitations centralized in `ml/features_module_d.py`; Module A fusion stays refused with a clean re-entry point (`MODULE_A_FUSION_ENABLED`).

## Mobile combined analysis API (`/api/v1/analyze`)
- `POST /api/v1/analyze` (JSON `url`/`message`/`active_call`; `text` accepted as a message alias) and multipart sibling `POST /api/v1/analyze/screenshot` (`image` file plus optional `url`/`message`/`active_call` fields) share one service
  (`services.analyze_mobile`) that reuses the single-channel analyzers and Module D fusion — no analysis logic in the routes.
- Mobile verdict carries risk level/score, one-line summary, evidence, per-channel URL/message/OCR findings, unavailable modules, limitations, recommended action plus a safety-action checklist.
- Message+screenshot pairs analyze both texts and fuse the higher-scoring one with embedded-URL evidence merged once; unassessable text still refuses with 503, never a false low risk.
- Client guidance (30 s JSON / 60 s screenshot timeouts, versioning, error codes, curl examples) in `docs/MOBILE_API.md` and the OpenAPI descriptions.

## Mobile client (`mobile/`, React Native + Expo + TypeScript)
- Working Expo app talking to the real backend (`POST /api/v1/analyze`,
  `POST /api/v1/analyze/screenshot`): splash with non-blocking health probe, home with the
  honesty disclaimer, URL / message / screenshot / combined scanners, reusable result screen
  (level badge, summary, score, per-channel findings with ML-vs-heuristics split, evidence cards,
  contributing vs not-analyzed modules, actions, expandable technical details), about/limitations.
- One centralized API client (env-driven base URL, per-endpoint timeouts, envelope + ApiError
  mapping); TypeScript interfaces mirror the v1 schemas; no ML logic on-device.
- Verified by `tsc --noEmit`, offline `node --test` units, and a live-backend smoke script
  (`mobile/scripts/check-backend.mjs`) against the real FastAPI server.
