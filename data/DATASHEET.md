# Module A datasheet — amount-only source-unit benchmark

**Status: no artifact, no metrics.** Module A cannot be trained in this checkout because the
authorized IEEE-CIS source is licensed and not redistributed. `ml/generate_module_a_data.py` stops
with an explicit `FileNotFoundError` rather than fabricating a substitute, and `/check-transaction`
returns **503** in that state. Nothing below is a current result.

**Do not present these metrics as real-world performance.**

## Current contract

`ml/features_module_a.py` owns the whole contract:

| Item | Value |
|---|---|
| Feature | `amount` — the only one |
| Unit | `ieee_cis_source`, asserted explicitly; INR or unspecified units are refused |
| Validation | finite, nonnegative, non-boolean, representable in float32 |
| Artifact contract | `FEATURE_CONTRACT` version 2, enforced by `validate_artifact()` |
| Rejected | any artifact with legacy six features, wrong `n_features_in_`, or classes != `[0, 1]` |

The response declares `analysis_scope: ieee_cis_amount_only_benchmark` and carries
`BENCHMARK_NOTICE`, which states that time, device, call state and transfer count are not used and
that the score is not a calibrated fraud probability.

## Source and choice

IEEE-CIS Fraud Detection, supplied locally by the user from the
[Kaggle competition](https://www.kaggle.com/competitions/ieee-fraud-detection/data), was chosen
because it contains observed anonymised transactions and fraud labels. PaySim better matches
mobile-money transfers but is simulated financial data, as
[its authors explain](https://github.com/EdgarLopezPhD/PaySim), so it does not meet the requirement
for real financial observations. IEEE-CIS instead concerns online card fraud, not labelled APP
coercion. **No claim is made that these domains transfer.** Use remains subject to the competition's
terms; raw files are not redistributed.

Only `train_transaction.csv` is used: 590,540 rows, 20,663 fraud (3.50%), 569,877 legitimate. No
sampling, class balancing by row generation, or label changes. Test transactions are unlabelled.
Identity files are not used: device descriptions do not establish device trust or per-user novelty,
and no call-state observations exist in the supplied files.

## Retained historical record (v1, six features, **disabled**)

The numbers below describe a model that no longer exists. `validate_artifact()` rejects its
artifacts, and the feature trace that produced them is superseded by
[Module A correctness](../docs/MODULE_A_CORRECTNESS.md). They are kept only so the audit trail of
*why* the features were removed is legible. **They are not current results and must not be quoted
as such.**

Removed features and why:

| Removed feature | Why it was removed |
|---|---|
| `hour_of_day` | `floor(TransactionDT / 3600) % 24` is a *relative* dataset phase, not local clock time; serving extracted a real UTC hour. |
| `is_odd_hour` | Same defect, one level down; no verified nighttime semantics. |
| `is_new_device` | IEEE-CIS establishes no device history, so the artifact's `device_counts` was empty and every API caller scored as new. |
| `is_active_call` | Synthesised per row *conditioned on the label*, with independent 12.5% bit flips. It encoded the answer. |
| `transaction_velocity` | Counted over a card tuple in the source; the UI supplied a per-device transfer count. Different entities, silently compared. |

Historical chronological holdout (split at `TransactionDT=12192900`, equal timestamps kept
together; 472,432 train / 118,108 test; same XGBoost parameters and 0.5 threshold in both arms):

| Model | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| With synthetic telemetry | 0.088106 | 0.686270 | 0.156163 | 0.253113 |
| Without synthetic telemetry | 0.058757 | 0.572343 | 0.106573 | 0.326725 |

The +11.39 pp recall delta is **manufactured** by the assumed label-conditioned signals present in
train *and* test. Class weighting makes the scores unsuitable as calibrated probabilities. The
hypothetical priors that produced them (`ml/module_a_priors.json`) were deleted; no reader remained
once the features were removed.

The stale `ml/models/module_a.metrics.json` report from that era was also removed, so no reader can
mistake it for a current artifact description. The figures above are the record.

## Reproduction

Once the authorized source is available, run from the repository root:

```powershell
.\.venv\Scripts\python.exe ml\generate_module_a_data.py --source <authorized-train_transaction.csv>
.\.venv\Scripts\python.exe ml\train_module_a.py
```

Generation validates the source and records SHA-256 hashes plus the feature contract. Training
rejects old generated-data contracts and uses the same chronological 80/20 split, XGBoost
parameters, class weighting and 0.5 evaluation threshold as before, so a feature fix is not mixed
with a tuning change. Model and report backups preserve previous results. Restart a running backend
after retraining to clear its model cache.

Compare real metrics only after training on the same authorized data; never infer them from the
regression fixtures, which are invented unit-test data created inside pytest's temporary directory.

## Operational limits

The predictor and the one-feature input contract are unchanged since the rewrite. Runtime clock time
and manually supplied velocity differ from anything in training and are ignored entirely.
`device_id` is optional legacy metadata with no effect on the score. Old hand-picked amount-boundary
demos are invalid.

Restoring real transaction assessment requires labelled data with justified units and features;
restoring transaction fusion additionally requires compatible retraining and evaluation of Module D
(see [ADR-006](../docs/decision_log.md)).

## Module D synthetic joint data

See [Module D datasheet](MODULE_D_DATASHEET.md). Its metrics are synthetic policy recovery, not
real-world performance. The Android companion adds an optional real phone report at inference; it
does not change anything in Module A training, and call state is not a model input.