# TrueIntent Build Decisions (Iterations 1–11)

Scoping and implementation decisions made during the build. Each entry cites the repo evidence —
no generic advice. Technical ADRs live in [`decision_log.md`](decision_log.md);
user-facing limitations live in [`LIMITATIONS.md`](LIMITATIONS.md).

## D-01 — Synthetic Module A dataset with documented assumptions
- **Decision:** Generate `data/raw/module_a_transactions.csv` synthetically (seed 42) instead of blocking on
  confidential bank/telephony telemetry: ~65% legitimate (₹100–12,000, ~8% coincidental calls, velocity 1–3)
  vs ~35% fraud (₹15,000–150,000, ~90% active-call correlation, velocity 3–10).
- **Evidence:** `ml/generate_module_a_data.py`, `data/README.md` (prominent synthetic-data warning).
- **Consequence:** Unblocks training, but the non-overlapping amount ranges make the data near-separable —
  the perfect 1.0/1.0/1.0/0.0 metrics must never be presented as real-world performance.

## D-02 — Rules-only Modules B/C until labeled data arrives (no fabricated training data)
- **Decision:** With `module_b_urls.csv`, `sms_spam_collection.csv`, and `signature_examples.csv` all absent,
  ship transparent fallbacks rather than fake ML: Module B runs named-weight rules and reports
  `ml_status: "rules_only (dataset pending)"`; Module C runs a documented keyword baseline.
  `train_module_b.py` / `train_module_c.py` print DATASET PENDING and exit cleanly.
- **Evidence:** `ml/predict_module_b.py`, `ml/predict_module_c.py`, `data/README.md` status table.
- **Consequence:** Fully demoable today; ML activates by dropping CSVs into `data/raw/` and re-running trainers.

## D-03 — Two behavioral signatures instead of one generic scam label
- **Decision:** Split Module C into `fear_authority` (digital-arrest coercion) vs `greed_opportunity`
  (fake-trading temptation), matching the two spec personas, with deterministic tie-break
  (fear wins ties) and a step scoring function (1 hit → 0.55, 2 → 0.75, 3+ → 0.9).
- **Evidence:** `FEAR_AUTHORITY_KEYWORDS` / `GREED_OPPORTUNITY_KEYWORDS` in `ml/predict_module_c.py`, ADR-002.
- **Consequence:** Explanations name the manipulation tactic, not just "scam".

## D-04 — Module C auto-folds Module B (URL-in-message pipeline)
- **Decision:** URLs extracted from message text are scored by `check_url()` and folded in as
  `final = max(text_score, url_score)` with `Embedded URL … flagged by Module B` reasons — so a benign
  message carrying a phishing link still scores high.
- **Evidence:** URL-folding block in `analyze_message()`, covered by `tests/test_integration.py`.
- **Consequence:** Module B's API weight in Module D stays low (0.25) without losing URL signal.

## D-05 — OCR failure contract: never a false low-risk score
- **Decision:** `analyze_image()` returns an `ocr_status` envelope (`ok` / `insufficient_text` /
  `ocr_unavailable` / `invalid_image`); short/garbled OCR output (< 20 chars or < 3 words) yields a
  "try a clearer screenshot" response at score 0.0 that callers must not read as clean. Missing-file
  validation runs before the OCR stack so absence is always `invalid_image`.
- **Evidence:** `ml/ocr_module_c.py`, `tests/test_module_c_ocr.py`.
- **Consequence:** Blurry screenshots degrade to guidance, not false reassurance; `/check-message`
  maps these to 200/400/503 appropriately.

## D-06 — No fabricated screenshot evidence in tests
- **Decision:** The evidence test skips until real screenshots land in gitignored `data/raw/screenshots/`.
  The only committed image is a programmatically generated, filename- and header-stamped
  `SYNTHETIC TEST FIXTURE — NOT REAL EVIDENCE` PNG, added only after explicit user approval, and its
  end-to-end test skips where the Tesseract binary is unavailable.
- **Evidence:** `tests/test_module_c_ocr.py`, `tests/data/synthetic_chat_fear_authority.png`.
- **Consequence:** Per SPEC §8's anti-fabrication instruction, extended to test fixtures.

## D-07 — Module D: renormalized weights + honesty rule + SHAP with labeled fallbacks
- **Decision:** Named weights A 0.45 / C 0.30 / B 0.25 renormalized over contributing modules only;
  tiers at 0.25/0.50/0.75; all-None raises instead of verdicting; explanations always list contributing
  vs skipped modules; SHAP via `TreeExplainer` for A and exact linear-SHAP tokens for C, with honestly
  labeled heuristic/keyword fallbacks (`details.shap_methods`).
- **Evidence:** `ml/predict_module_d.py`, ADR-005, escalation proof in `tests/test_integration.py`.
- **Consequence:** Single-module checks still span 0–1; known tradeoff is renormalization dilution
  (benign extra inputs lower a scary score) — documented in LIMITATIONS.

## D-08 — Backend: strict input contracts, offline-safe inference
- **Decision:** Pydantic v2 schemas mirroring `data/schema.md`; `/check-message` takes exactly one of
  text/image (10 MB cap, image-type allowlist); malformed URLs → 422, unreadable images → 400,
  missing OCR/model → 503; all module calls use `fetch_live_page=False` for deterministic responses;
  CORS restricted to local origins via regex.
- **Evidence:** `backend/app/main.py`, `backend/app/schemas.py`, `tests/backend/test_api.py` (13 tests).
- **Consequence:** Module B's live-fetch/login-form signals are dormant via the API (documented gap).

## D-09 — Frontend optimized for the senior-citizen persona
- **Decision:** Calm light theme, large type, plain reassuring copy ("Pause together. Check before you send."),
  solid tier colors with per-tier gentle guidance, single shared `Results` card, loading spinners and
  server-unreachable messaging on every view. No red flashing or alarming iconography.
- **Evidence:** `frontend/src/App.jsx`, `frontend/src/components/Results.jsx`.
- **Consequence:** Deliberately undramatic — a Critical result still reads as guidance, not an alarm.

## D-10 — Privacy by design in version control
- **Decision:** `data/raw/*`, `*.pkl`/`*.joblib`, venvs, and `node_modules` are gitignored; only synthetic
  data and code are committed. No screenshots, transaction PII, or model binaries enter git.
- **Evidence:** `.gitignore`, ADR-001.
- **Consequence:** Reviewers retrain Module A locally (`ml/train_module_a.py` regenerates deterministically).

## D-11 — Spec deltas: no database, no frontend tests, no Docker
- **Decision:** Deferred SPEC §7 items with no implementation: SQLite (nothing is persisted at all —
  consistent with privacy-by-design), React Testing Library (no frontend test runner is configured),
  Docker packaging. Backend coverage is pytest + TestClient + pytest-cov instead.
- **Evidence:** Absence in repo; `backend/requirements.txt` (pytest, httpx, pytest-cov), `docs/coverage.md`.
- **Consequence:** Stated as limitations, not silent omissions.
