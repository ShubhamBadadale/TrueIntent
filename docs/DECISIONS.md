# TrueIntent Build Decisions

Scoping and implementation decisions made during the build. Each entry cites the repo evidence —
no generic advice. Technical ADRs live in [`decision_log.md`](decision_log.md); user-facing
limitations live in [`LIMITATIONS.md`](LIMITATIONS.md); superseded decisions are annotated in
place rather than deleted, so the reasoning trail stays readable.

## D-01 — Module A ingests authorized IEEE-CIS data and generates nothing
- **Decision:** `ml/generate_module_a_data.py` reads an authorized `train_transaction.csv` and
  writes `amount` plus real labels in the original source unit. It refuses to run when the source
  is absent, and never synthesises call/device flags or a substitute dataset. The earlier
  synthetic generator (seed 42, disjoint amount ranges, hypothetical call priors) was removed
  together with `ml/module_a_priors.json`, because label-conditioned synthetic telemetry cannot be
  presented as coercion detection.
- **Evidence:** `ml/generate_module_a_data.py`, `ml/features_module_a.py`,
  [Module A correctness](MODULE_A_CORRECTNESS.md).
- **Consequence:** Module A cannot be trained or demonstrated in this checkout. That is the
  intended, honest outcome — an unavailable model returns 503, not a plausible substitute.

## D-02 — No fabricated training data; trainers report DATASET PENDING
- **Decision:** `ml/train_module_b.py` and `ml/train_module_c.py` print `DATASET PENDING` and exit
  cleanly when their CSV is absent, and the API reports the corresponding unavailable/fallback
  state. Nothing is padded, templated or invented to make a trainer succeed.
- **Evidence:** `ml/train_module_b.py`, `ml/train_module_c.py`, `data/README.md` status table.
- **Consequence:** Fully demoable offline; ML activates by dropping real CSVs into `data/raw/` and
  re-running the trainers. The obsolete `ml/scripts/generate_signature_examples.py`, which wrote an
  incompatible two-column CSV over the real artifact at the same path, was deleted.

## D-03 — Two behavioural signatures on top of a ten-class intent model
- **Decision:** Module C models ten specific intents and separately reports the two psychology
  labels `fear_authority` / `greed_opportunity` via a compatibility model, so explanations can name
  the manipulation tactic without flattening the taxonomy. Keyword lists are retained only as
  measured-ablation candidates; the shipped artifact has `retained_rules: []`.
- **Evidence:** `ml/features_module_c.py` (`INTENTS`, `LEGACY_MAP`), `ml/evaluate_module_c.py`.
- **Consequence:** Explanations name the tactic, and no unvalidated keyword score can be presented
  as an ML finding.

## D-04 — Module C auto-folds Module B (URL-in-message pipeline)
- **Decision:** URLs extracted from message text are scored by `check_url()` and folded in as
  `max(text_score, url_score)` with `Embedded URL … flagged by Module B` reasons. Module D
  separately reconstructs a text-only C score when the artifact provides `text_score`, so a shared
  link is never counted as two independent signals.
- **Evidence:** URL-folding block in `ml/predict_module_c.py::analyze_message`;
  `tests/test_module_d_interactions.py::test_embedded_url_is_not_a_second_message_signal`.
- **Consequence:** A benign message carrying a phishing link still scores high without inflating
  the correlation layer.

## D-05 — OCR failure contract: never a false low-risk score
- **Decision:** `analyze_image()` returns an `ocr_status` envelope (`ok` / `insufficient_text` /
  `ocr_unavailable` / `invalid_image`); short or garbled OCR output (< 20 chars or < 3 words)
  yields a "try a clearer screenshot" response at score 0.0 that callers must not read as clean.
  Missing-file validation runs before the OCR stack, so absence is always `invalid_image`.
- **Evidence:** `ml/ocr_module_c.py`, `tests/test_module_c_ocr.py`.
- **Consequence:** Blurry screenshots degrade to guidance, not false reassurance; `/check-message`
  maps these to 200/400/503 appropriately.

## D-06 — No fabricated screenshot evidence in tests
- **Decision:** The evidence test skips until real screenshots land in gitignored
  `data/raw/screenshots/`. The only committed image is a programmatically generated,
  filename- and header-stamped `SYNTHETIC TEST FIXTURE — NOT REAL EVIDENCE` PNG, added only after
  explicit user approval, and its end-to-end test skips where the Tesseract binary is unavailable.
- **Evidence:** `tests/test_module_c_ocr.py`, `tests/data/synthetic_chat_fear_authority.png`.
- **Consequence:** Spec §8's anti-fabrication instruction, extended to test fixtures.

## D-07 — Module D: availability-aware interactions, honest reporting, coefficient-level explanation
- **Decision:** Module D uses a `format_version: 2` logistic policy over fourteen features that
  include explicit presence flags (`a_present`, `b_present`, `c_present`), `call_known`, tactic
  signals and four cross-channel interactions gated by presence. Tiers are 0.25/0.50/0.75;
  all-`None` raises instead of verdicting; explanations always list contributing vs skipped
  modules. Legacy three-score artifacts remain readable, and fixed renormalized weights
  (A 0.45 / B 0.25 / C 0.30) apply only when no artifact exists — a state the response labels.
- **Evidence:** `ml/features_module_d.py`, `ml/predict_module_d.py`, `ml/evaluate_module_d.py`.
- **Consequence:** Missing evidence is modelled as missing, not as zero risk. Attribution is exact
  coefficient products for a linear model, and the response says interactions are not independent
  causal effects.

## D-08 — Backend: strict input contracts, offline-safe inference
- **Decision:** Pydantic v2 schemas mirroring `data/schema.md`; `/check-message` takes exactly one
  of text/image (10 MB cap, image-type allowlist); malformed URLs → 422, unreadable images → 400,
  missing OCR or model → 503; every module call uses `fetch_live_page=False`; CORS restricted to
  local origins by regex.
- **Evidence:** `backend/app/main.py`, `backend/app/schemas.py`, `tests/backend/test_api.py`.
- **Consequence:** Deterministic, egress-free responses; module unavailability is a status code, not
  a silent degraded number.

## D-09 — Frontend optimized for the senior-citizen persona
- **Decision:** Calm light theme, large type, plain reassuring copy, solid tier colours with per-tier
  gentle guidance, a single shared results card, loading spinners and server-unreachable messaging
  on every view. No red flashing or alarming iconography. Every index is labelled as uncalibrated.
- **Evidence:** `frontend/src/App.jsx`, `frontend/src/components/Results.jsx`.
- **Consequence:** Deliberately undramatic — a Critical result still reads as guidance, not an alarm.

## D-10 — Privacy by design in version control
- **Decision:** `data/raw/*`, `*.pkl`/`*.joblib`, virtualenvs and `node_modules` are gitignored.
  Only synthetic data and code are committed. No screenshots, transaction PII, or model binaries
  enter git.
- **Evidence:** `.gitignore`, ADR-001.
- **Consequence:** A fresh clone must regenerate artifacts. Module D alone is reproducible from a
  clean checkout; Modules A/B/C depend on external sources.

## D-11 — Docker packaging that never trains
- **Decision:** `backend/Dockerfile` installs the runtime requirements and the Tesseract binary but
  trains nothing; `docker-compose.yml` bind-mounts `./ml/models` read-only. The earlier
  build-time Module A retraining was removed together with the synthetic dataset it depended on.
- **Evidence:** `backend/Dockerfile`, `docker-compose.yml`, `README.md`.
- **Consequence:** Builds are deterministic and offline-safe; a missing model degrades to the
  explicit unavailable/fallback behaviour.

## D-12 — Deferred spec items
- **Decision:** SQLite persistence is skipped entirely (nothing is stored server-side, consistent
  with privacy-by-design) and React Testing Library is not used. The frontend is regression-tested
  with `node --test` rendering the real components through `react-dom/server`.
- **Evidence:** absence in repo; `frontend/tests/*.test.mjs`, `docs/LIMITATIONS.md` Part C.
- **Consequence:** Stated as limitations, not silent omissions.

## D-13 — Repository audit pass
- **Decision:** A full audit (`docs/AUDIT_REPORT.md`) removed unreachable training/generation code,
  repaired broken direct-script imports, unified the virtualenv location on `.venv/`, split runtime
  from test dependencies, added `pytest.ini` and `.env.example`, and corrected every documentation
  claim that contradicted the code. Verified endpoints were re-measured against a running backend.
- **Evidence:** `docs/AUDIT_REPORT.md`.
- **Consequence:** Documentation now describes what the code does, including the parts that are
  unavailable.