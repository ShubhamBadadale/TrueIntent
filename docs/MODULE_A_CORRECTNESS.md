# Module A correctness update

## Decision

Retain XGBoost only as an **amount-only IEEE-CIS source-unit benchmark**. There is
no verified currency conversion or real APP-fraud telemetry dataset. Do not infer
INR risk, nighttime behavior, device novelty or call-related coercion from this
data. Removing features requires retraining; old model artifacts cannot be reused
by zeroing their inputs. No replacement production artifact was fabricated.

## Feature trace

| Feature | Training meaning (v1) | Inference meaning (v1) | Problem | Fix in v2 |
|---|---|---|---|---|
| amount | Unchanged IEEE-CIS TransactionAmt | Frontend rupee amount; explanation displays INR | Source units have no verified INR mapping | Retain only for explicit ieee_cis_source benchmark input; reject INR/missing units; no exchange-rate guess |
| hour_of_day | floor(TransactionDT / 3600) modulo 24 | Hour from supplied ISO timestamp; browser converts local time to UTC | Relative dataset phase is not known local clock time; equivalent offset representations can differ | Remove feature and time control/conversion; retain TransactionDT solely for chronological splitting |
| is_odd_hour | Relative phase below 6 or at/above 23 | Real-clock late-night flag | Neither training nighttime semantics nor serving timezone matches | Remove feature and nighttime explanations |
| is_new_device | Label-conditioned Bernoulli simulation plus bit flips | Explicit flag or count <= 2 in artifact device_counts | Artifact map is empty, so every API device becomes new; no measured history | Remove feature and device lookup; IDs are optional legacy metadata |
| is_active_call | Label-conditioned synthetic signal | Manual checkbox or unattested Android report | No observed call/outcome relationship in IEEE-CIS | Remove feature and call-risk explanations; retain legacy input validation only |
| transaction_velocity | Prior-hour count for card1/card2/addr1 tuple | Manual transfers/device count, default 1 | Different history entity and measurement; missing source keys previously become zero | Remove feature and transfer-count UI |

Source ingestion copies amount and labels, retains source IDs/time for audit/split,
and adds the explicit unit assertion. It generates no synthetic flags and reads
no card/address columns. The historical module_a_priors.json is unused.

## Shared contract and API behavior

`ml/features_module_a.py` owns the exact feature order, numeric validation,
unit requirement and versioned artifact contract. Generator, trainer, predictor
and offline explanation feature preparation all use it. Amounts must be finite,
nonnegative and representable by XGBoost. Source zero amounts are consistently
accepted; booleans, negative/nonfinite values and overflow are rejected.

- `/check-transaction` requires explicit source-unit opt-in to score. Requests
  omitting units retain an INR default and receive 422 rather than being silently
  relabelled. Device IDs are no longer required. Legacy timestamp/telemetry fields
  are validated but cannot influence predictions.
- Missing, corrupt or legacy artifacts produce 503, never a default safe score.
  Artifact caching notices file replacement; a version/feature mismatch is rejected.
- Successful responses carry `analysis_scope: ieee_cis_amount_only_benchmark`
  and the limitation notice. The web UI displays a neutral benchmark score,
  without transfer-risk tiers or advice based on that score.
- Transaction-bearing `/check-combined` requests return 422. The existing D
  policy was fitted on the obsolete A distribution; silently substituting v2
  would be another train/inference mismatch. URL/text-only routes remain available.
  Direct fusion of transaction-context dictionaries and D scenario generation
  from the new A artifact are also refused. Numeric D policy experiments remain.
- A explanation preprocessing shares the contract. Removed-feature templates and
  heuristic call/device/nighttime fallbacks are gone. Failed SHAP yields no
  invented contributors.

Example benchmark request (amount must come from the source dataset):

```json
{"amount": 500.0, "amount_unit": "ieee_cis_source"}
```

## Training and metrics

Production retraining is required but **not completed**: neither the authorized
IEEE-CIS source, generated dataset nor model binaries exist in this checkout.
Running `ml/train_module_a.py` stops at the missing-source check, with no generated
data/model. No dataset was downloaded or synthesized for production training.

| Metric | Historical six-feature chronological holdout | New amount-only model |
|---|---:|---|
| Precision | 0.088106 | Not measured |
| Recall | 0.686270 | Not measured |
| F1 | 0.156163 | Not measured |
| False-positive rate | 0.253113 | Not measured |

The historical report `ml/models/module_a.metrics.json` is retained unchanged.
Its old four-feature no-telemetry ablation is **not** an amount-only evaluation.
No accuracy improvement is claimed. Correctness here means removing unsupported
interpretations and failing explicitly when a valid assessment is unavailable.

Once the authorized source is available, run from the repository root:

```powershell
.\.venv\Scripts\python.exe ml/generate_module_a_data.py --source <authorized-train_transaction.csv>
.\.venv\Scripts\python.exe ml/train_module_a.py
```

Generation validates source data and records hashes and the feature contract.
Training rejects old generated-data contracts and uses the same chronological
80/20 split with equal timestamps kept together, XGBoost parameters, class weighting
and 0.5 evaluation threshold as before, to avoid mixing feature fixes with tuning.
Model/report backups preserve previous results. Compare actual metrics only after
training on the same authorized data; do not infer them from regression fixtures.

## Validation and limits

Verification on this checkout: Python suite **112 passed, 6 skipped**; frontend
regressions **3 passed**; frontend production build and lint passed. Skips cover
missing real B/C artifacts and OCR engine/evidence. Two existing Starlette
deprecation warnings remain. No real Module A retraining metrics were produced.

Regression coverage includes feature parity, timezone/ID/telemetry invariance,
invalid amount/unit rejection, missing/corrupt/old artifacts, cache invalidation,
chronological boundaries, provenance rejection, API errors, fusion exclusion,
neutral benchmark rendering and frontend request payloads.

Unit tests create a tiny, explicitly invented training fixture only in pytest's
temporary directory to test training/serialization/serving mechanics. Its metrics
are not production results. Existing optional B/C model tests and real OCR tests
remain dependent on external artifacts/engine/evidence.

The benchmark still concerns historical online-card fraud, not APP coercion.
Amount alone may perform poorly. Class weighting and the unchanged evaluation
threshold do not produce calibrated probabilities. Restoring real transaction
assessment requires appropriately labelled data with justified units and features;
restoring transaction fusion also requires compatible training and evaluation of D.
