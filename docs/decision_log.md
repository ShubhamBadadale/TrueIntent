# Decision Log

## ADR-001: Project Architecture & Scaffolding Strategy
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: TrueIntent requires a modular structure isolating ML model pipelines, backend API logic, frontend presentation, data stores, tests, and project documentation.
- **Decision**: 
  - Monorepo folder structure with `/backend` (FastAPI), `/frontend` (React), `/ml` (training scripts, notebooks, models), `/data` (raw & processed), `/tests`, and `/docs`.
  - Privacy-by-design: `data/raw/*` is strictly ignored in git to ensure zero user PII or raw transaction leaks into source control.
- **Consequences**: Enables clean separation of concerns and step-by-step modular implementation across iterations.

---

## ADR-002: Dataset Sourcing Strategy & Module C Classifier Architecture
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**:
  - Module A requires transaction + call state telemetry; synthetic data generated due to confidential telephony-bank telemetry.
  - Module B dataset (URLs) to be provided as a real dataset by project owner at `data/raw/module_b_urls.csv`.
  - Module C requires both binary scam vs. legitimate classification and fine-grained psychological manipulation signature identification (`fear_authority`, `greed_opportunity`, `none`).
- **Decision**:
  - **Module A**: Synthetic dataset (`data/raw/module_a_transactions.csv`) created with explicit APP fraud assumptions (90% call correlation for fraud vs 8% for legitimate).
  - **Module B**: Real dataset (`data/raw/module_b_urls.csv`) provided by user.
  - **Module C Classifier Architecture (Two-Stage Pipeline)**:
    - **Stage 1 (Binary Scam Detector)**: Train a base TF-IDF / Logistic Regression / BERT classifier on `data/raw/sms_spam_collection.csv` for general scam/legitimate detection.
    - **Stage 2 (Signature Classifier)**: Use `data/raw/signature_examples.csv` as a fine-tuned secondary classifier or rules-augmented pattern matching layer to identify `fear_authority` vs `greed_opportunity` tactics on messages flagged as scams.
- **Consequences**: Clean separation of base scam detection and specialized psychological signature classification without data leakage or overfitting on small curated samples.

---

## ADR-003: Module A Telemetry Feature Engineering Strategy (`timestamp` & `device_id`)
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**:
  - `timestamp` (ISO 8601 string) and `device_id` (string identifier) are raw telemetry fields provided in Module A transaction records.
  - Feeding raw string `timestamp` or high-cardinality categorical `device_id` strings directly into gradient boosted trees causes severe overfitting or loss of temporal signals.
- **Decision**:
  - **`timestamp` Transformation**: Extracted `hour_of_day` (integer 0–23) and derived `is_odd_hour` (binary flag = 1 if hour < 6 or >= 23, representing late-night / off-peak fraud urgency windows).
  - **`device_id` Transformation**: Processed into `is_new_device` (binary flag = 1 if the device transaction count in history <= 2, representing unrecognised or newly associated devices).
- **Consequences**: Captures key temporal and device-switching risk signals without overfitting tree splits to specific string IDs or exact timestamps.

---

## ADR-004: Module B URL Safety Scoring Weights & Page Inspection Strategy
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**:
  - URL safety evaluation requires combining structural string analysis with target destination signals.
  - Phishing attacks frequently rely on IP hosting, brand typosquatting, unencrypted HTTP, obfuscated redirects, and fraudulent login forms.
- **Decision**:
  - **Option (a) Lightweight Live Page Fetching**: Added a 2.0-second timeout HTTP inspect step to follow redirects and check destination HTML for login forms (`<form>`, `type="password"`). If connection times out or fails, gracefully falls back to URL string rules without crashing.
  - **Named Rule Weight Constants**:
    - `WEIGHT_IP_ADDRESS = 0.40`
    - `WEIGHT_TYPOSQUATTING = 0.35`
    - `WEIGHT_LOGIN_FORM_PRESENT = 0.25`
    - `WEIGHT_INSECURE_HTTP = 0.20`
    - `WEIGHT_SUSPICIOUS_TLD = 0.20`
    - `WEIGHT_URL_OBFUSCATION = 0.15`
    - `WEIGHT_SUSPICIOUS_LENGTH = 0.10`
  - **Score Combination**: Cumulative rule risk capped at 1.0 (`min(1.0, sum(active_weights))`). When the ML model is trained, `final_score = 0.50 * rule_score + 0.50 * ml_score`.
- **Consequences**: Provides deterministic, explainable risk flags with transparent weight caps, supplemented by live destination analysis when reachable.


---

## ADR-005: Module D Unified Scoring Weights, Tiers & SHAP Explanation Strategy
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**:
  - Module D must fuse heterogeneous module scores (transaction+call, URL, message) into one tier without letting a skipped module dilute or inflate the result, and must explain *why* in plain language (the project's core thesis).
  - SHAP must ground the explanation in the actual models where feasible, with honest fallbacks where it is not (Module C is rules-only until its dataset arrives; SHAP library may be absent).
- **Decision**:
  - **Named weight constants** in `ml/predict_module_d.py`: `WEIGHT_MODULE_A = 0.45` (core thesis signal), `WEIGHT_MODULE_C = 0.30` (manipulation language), `WEIGHT_MODULE_B = 0.25` (narrowest; often already folded into C). Weights renormalize over contributing modules only; all-None raises `ValueError` instead of returning a false verdict.
  - **Named tier thresholds**: `TIER_LOW_MAX = 0.25`, `TIER_MEDIUM_MAX = 0.50`, `TIER_HIGH_MAX = 0.75` (>= 0.75 -> Critical).
  - **SHAP**: Module A uses `shap.TreeExplainer` on the XGBoost model (top positive contributors only, value-aware templates); Module C uses exact linear-SHAP token attribution (coef x TF-IDF, mathematically equal to SHAP for a linear model) when an ML artifact + input text are present, else keyword evidence. Headline takes one factor per risky module round-robin (max 3) so no module crowds out the others; URL reasons severity-ranked (IP/typosquatting first).
  - **Honesty rule**: explanation always lists contributing vs. skipped modules; skipped modules are never implied to have run.
- **Consequences**: Deterministic, tunable fusion with model-grounded explanations; graceful degradation to rule reasons when SHAP/ML artifacts are unavailable.



