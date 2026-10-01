# Decision Log

Architecture decision records. Entries marked **Superseded** describe an approach that was tried and
removed; they are kept so the reasoning trail stays auditable.

---

## ADR-001: Project Architecture & Scaffolding Strategy
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: TrueIntent requires a modular structure isolating ML model pipelines, backend API logic, frontend presentation, data stores, tests, and project documentation.
- **Decision**:
  - Monorepo folder structure with `/backend` (FastAPI), `/frontend` (React), `/ml` (training scripts, notebooks, models), `/data` (raw & processed), `/tests`, and `/docs`.
  - Privacy-by-design: `data/raw/*` is strictly ignored in git to ensure zero user PII or raw transaction leaks into source control.
- **Consequences**: Enables clean separation of concerns and step-by-step modular implementation across iterations.

---

## ADR-002: Dataset Sourcing Strategy
- **Date**: 2026-09-12
- **Status**: Superseded in part
- **Context**:
  - Module A requires transaction + call-state telemetry. No public dataset links call state to authorised-payment fraud.
  - Module B needs labelled phishing vs legitimate URLs.
  - Module C needs labelled scam text with a behavioural signature taxonomy.
- **Decision (as originally recorded)**:
  - Module A: a synthetic dataset with documented APP-fraud assumptions.
  - Module B: a real dataset supplied by the project owner.
  - Module C: a two-stage pipeline — a binary scam detector over an SMS spam corpus, then a signature classifier or rules-augmented layer to separate `fear_authority` from `greed_opportunity`.
- **Superseded by**:
  - Module A no longer generates a synthetic substitute. Authorized IEEE-CIS source data is required and its absence is reported explicitly (ADR-006).
  - Module C is a single ten-class intent model evaluated with grouped cross-validation, not a two-stage pipeline, because the two-stage split leaked the signature task into the detector.
- **Consequences**: Dataset provenance is now explicit per module, and no stage invents data.

---

## ADR-003: Module A Telemetry Feature Engineering (`timestamp` & `device_id`)
- **Date**: 2026-09-12
- **Status**: **Superseded by ADR-006**
- **Context**:
  - `timestamp` (ISO 8601) and `device_id` (string) are raw fields provided in Module A records.
  - Feeding raw strings directly into gradient-boosted trees causes overfitting or loss of temporal signal.
- **Decision (as originally recorded)**:
  - `timestamp` → `hour_of_day` (0–23) and `is_odd_hour` (< 6 or >= 23).
  - `device_id` → `is_new_device` (historical count <= 2).
- **Why it was reversed**:
  - `TransactionDT` is a *relative* dataset phase, not local clock time; `hour_of_day` therefore meant something different at training and at serving.
  - IEEE-CIS establishes no device history, so `device_counts` was empty and every API caller became "new device".
  - No observed relationship links call state or device novelty to card fraud, and the synthetic
    stand-ins were conditioned on the label.
- **Consequences**: All five features were removed. Only `amount` survives, in the explicit source
  unit, and the removed-feature explanation templates are gone.

---

## ADR-004: Module B URL Safety Scoring Weights & Page Inspection Strategy
- **Date**: 2026-09-12
- **Status**: Amended (live fetching withdrawn)
- **Context**:
  - URL safety evaluation requires combining structural string analysis with target destination signals.
  - Phishing attacks rely on IP hosting, brand typosquatting, unencrypted HTTP and obfuscated redirects.
- **Decision**:
  - **Live page fetching was withdrawn.** Fetching a user-supplied URL from the server is an SSRF
    vector (link-local metadata endpoints, internal hosts) and makes responses non-deterministic.
    `inspect_live_page()` remains as a no-network compatibility stub that performs no I/O and
    contributes **no** score weight; `WEIGHT_LOGIN_FORM_PRESENT` and the login-form branch were
    deleted because they were unreachable.
  - **Named rule weight constants** in `ml/predict_module_b.py`:
    - `WEIGHT_IP_ADDRESS = 0.40`
    - `WEIGHT_TYPOSQUATTING = 0.35`
    - `WEIGHT_INSECURE_HTTP = 0.20`
    - `WEIGHT_SUSPICIOUS_TLD = 0.20`
    - `WEIGHT_URL_OBFUSCATION = 0.15`
    - `WEIGHT_SUSPICIOUS_LENGTH = 0.10`
  - **Score combination**: cumulative rule risk capped at 1.0 (`min(1.0, sum(active_weights))`);
    when the classifier is available, `final_score = 0.50 * rule_score + 0.50 * ml_score`.
- **Consequences**: Deterministic, explainable, egress-free risk flags. Redirect chains, page content
  and security headers are **not** inspected — a real, documented capability gap.

---

## ADR-005: Module D Unified Scoring, Tiers & Explanation Strategy
- **Date**: 2026-09-12
- **Status**: Amended (v2 interaction policy)
- **Context**:
  - Module D must fuse heterogeneous module scores into one tier without letting a skipped module dilute or inflate the result, and must explain *why* in plain language.
  - SHAP must ground the explanation in the actual models where feasible, with honest fallbacks otherwise.
- **Decision (v1, still the fallback)**:
  - **Named weight constants** in `ml/predict_module_d.py`: `WEIGHT_MODULE_A = 0.45`,
    `WEIGHT_MODULE_C = 0.30`, `WEIGHT_MODULE_B = 0.25`, renormalized over contributing modules only;
    all-`None` raises `ValueError` instead of returning a false verdict.
  - **Named tier thresholds**: `TIER_LOW_MAX = 0.25`, `TIER_MEDIUM_MAX = 0.50`,
    `TIER_HIGH_MAX = 0.75`.
- **Decision (v2, current serving contract)**:
  - Fourteen features in `ml/features_module_d.py` add `a_present` / `b_present` / `c_present`,
    `call_known`, `credential_request`, `authority_fear`, and four presence-gated interactions
    (`message_transaction`, `call_transaction`, `url_credentials`, `authority_transaction`).
    A missing channel is modelled as absent, never as zero risk.
  - Explanations report exact coefficient products (mathematically the linear-SHAP attribution
    against a zero reference) and state that interactions are not independent causal effects.
- **Consequences**: A shared URL folded into Module C is not counted twice, and unknown call state is
  distinguishable from "no call".

---

## ADR-006: Module A is an amount-only source-unit benchmark
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**:
  - Module A's original features did not mean the same thing at training and at serving, and its
    synthetic telemetry was label-conditioned (see ADR-003).
  - There is no verified currency mapping from IEEE-CIS source units to INR, and no dataset links
    call state to authorised-payment fraud.
- **Decision**:
  - Retain XGBoost as a **one-feature benchmark** over `amount` in the original IEEE-CIS source
    unit. `FEATURE_CONTRACT` in `ml/features_module_a.py` is versioned and enforced by
    `validate_artifact()`; legacy six-feature artifacts are rejected outright.
  - `/check-transaction` requires an explicit `amount_unit: "ieee_cis_source"`. Omitting it leaves
    the `INR` default and returns 422 rather than silently relabelling a rupee amount.
  - Transaction-bearing `/check-combined` requests return 422, and `compute_unified_score()` refuses
    transaction-context dictionaries outright. The Module D policy was fitted on a different A
    distribution, so substituting v2 would be another train/inference mismatch.
  - Missing, corrupt or legacy artifacts produce 503, never a default safe score. Legacy
    `timestamp`, `device_id`, `is_active_call` and `transaction_velocity` fields are still validated
    for shape, but are documented as metadata and are never model features.
- **Consequences**: The project cannot score real transfers and says so. Restoring INR assessment
  requires labelled data with justified units and features; restoring transaction fusion requires
  compatible retraining and evaluation of Module D.

---

## ADR-007: Versioned v1 API alongside frozen legacy routes
- **Date**: 2026-10-01
- **Status**: Approved
- **Context**:
  - The API must eventually serve a mobile client reliably: JSON end to end (no multipart for
    text), stable machine-readable error codes, correlation IDs, readiness reporting, and
    documented limits.
  - The web portal, the Android companion drafts and the existing suite depend on the flat
    `/check-*` bodies and `{"detail": …}` errors; changing them would break clients for no
    behavioural gain.
- **Decision**:
  - Add `/api/v1/*` with success/error envelopes, a shared service layer, and the legacy routes
    kept as thin adapters that preserve byte-identical bodies. New behaviour goes to v1 only;
    legacy routes are frozen, not extended.
  - Standardise the failure surface in `backend/app/errors.py` (append-only codes), enforce
    response shapes with `response_model`, verify uploads by magic bytes rather than declared
    MIME, bound every read, offload every blocking call, and report readiness per component with
    explicit degraded/not-ready semantics.
  - Start the server with one command, `python -m backend` (`backend/__main__.py`); configure
    CORS, logging and all limits through `TRUEINTENT_*` environment variables.
- **Consequences**: Two presentations of the same logic, but a single source of every decision —
    the service layer. A future mobile client integrates against `docs/API_V1.md` without touching
    the portal contract.