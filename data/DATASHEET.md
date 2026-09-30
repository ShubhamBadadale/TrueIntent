# Module A datasheet — Phase 2

**Do not present these metrics as real-world performance.**

**Historical v1 results below.** The six-feature model is disabled and its artifacts
are rejected. Current code supports only an explicitly labelled source-unit,
amount-only research benchmark, requiring retraining. No measured v2 results are
available in this checkout. See [Module A correctness update](../docs/MODULE_A_CORRECTNESS.md).

## Source and choice

IEEE-CIS Fraud Detection, provided locally by the user from the
[Kaggle competition](https://www.kaggle.com/competitions/ieee-fraud-detection/data),
was chosen because it contains observed anonymized transactions and fraud labels.
PaySim better matches mobile-money transfers but is simulated financial data, as
[its authors explain](https://github.com/EdgarLopezPhD/PaySim), so it does not meet
the requirement for real financial observations. IEEE-CIS instead concerns online
card fraud, not labeled APP coercion. No claim is made that these domains transfer.
Use remains subject to the competition's terms; raw files are not redistributed.

Only train_transaction.csv is used: 590,540 rows, 20,663 fraud (3.50%), 569,877
legitimate. No sampling, class balancing by row generation, or label changes.
Test transactions are unlabeled; sample_submission probabilities are placeholders.
Identity files are not used: device descriptions do not establish device trust or
per-user novelty. No call-state observations exist in the supplied files.

## Exact six-feature contract

| Feature | Origin | Definition and limitation |
|---|---|---|
| amount | Real | TransactionAmt unchanged; source units retained, no claim of INR conversion. |
| hour_of_day | Real-derived proxy | floor(TransactionDT / 3600) modulo 24. Relative phase, not known local clock time. |
| is_odd_hour | Real-derived proxy | Existing hour < 6 or hour >= 23 rule on relative phase; not verified nighttime. |
| transaction_velocity | Real-derived proxy | Count in [t-3600,t) sharing complete card1/card2/addr1 tuple. Excludes current and all simultaneous transactions. Tuple collisions/splits mean this is not verified customer history. |
| is_new_device | Synthetic in every row | Bernoulli draw conditioned on fraud label, then independent bit flip. No real device-trust history. |
| is_active_call | Synthetic in every row | Bernoulli draw conditioned on fraud label, then independent bit flip. No observed phone calls. |

74,115 rows have incomplete history keys: velocity is zero (no inferred history),
not a measured absence of activity. Historical holdout events may use earlier
holdout transactions as observable history, never their labels or future events.
TransactionID and TransactionDT are audit/split columns, not model features.
There is no invented timestamp, beneficiary, overlay, device ID or extra feature.

## Assumptions and noise

Tunable configuration: ml/module_a_priors.json, seed 42.

| Synthetic flag | P(flag=1 given fraud) | P(flag=1 given legitimate) | Expected after noise (fraud / legitimate) |
|---|---:|---:|---:|
| is_active_call | 0.60 | 0.10 | 0.575 / 0.200 |
| is_new_device | 0.45 | 0.15 | 0.4625 / 0.2375 |

These are hypothetical scenario parameters authorized by the user, **not empirical
estimates or probabilities supported by a citation**. Moderate call enrichment
and weaker device enrichment test the hypothesis with overlap rather than nearly
encoding the outcome. They do not describe measured IEEE-CIS behavior. Each flag
is independently flipped with probability 0.125; effective probability is
0.125 + 0.75*p. Observed flip rates: call 12.4935%, device 12.4493%.
Real isFraud labels are never flipped. Noise does not guarantee imperfect F1;
training refuses to publish a perfect-F1 artifact pending investigation.

## Evaluation and ablation

Chronological split at TransactionDT=12192900, with equal timestamps kept together:
472,432 training rows (16,599 fraud), 118,108 held-out rows (4,064 fraud).
Same XGBoost parameters and fixed 0.5 threshold in both arms: 100 trees, depth 4,
learning rate 0.1, seed 42, hist trees; train-only negative/positive weight 27.46147.
No tuning on the holdout. The saved six-feature model is fitted only to training
rows; no refit incorporating held-out labels. Ablation removes both synthetic flags.

| Model | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| With synthetic telemetry | 0.088106 | 0.686270 | 0.156163 | 0.253113 |
| Without synthetic telemetry | 0.058757 | 0.572343 | 0.106573 | 0.326725 |

Recall delta: **+0.113927 (+11.39 percentage points)**. With telemetry:
TN=85178, FP=28866, FN=1275, TP=2789. Without: TN=76783, FP=37261, FN=1738, TP=2326.
The gain is manufactured by the assumed label-conditioned signals in train AND test,
not evidence of real call telemetry effectiveness. Precision is poor and FPR is high.
Class weighting makes scores unsuitable as calibrated fraud probabilities.
The four-feature ablation uses only real-derived inputs, but still has proxy/domain
limitations and does not establish deployment performance. Neither model is perfect.

## Reproduction and operational limits

From the repo root, with the authorized source files already in data/raw/ieee_cis:

```powershell
python ml/generate_module_a_data.py
python ml/train_module_a.py
python -m pytest tests/test_module_a.py tests/test_module_a_data.py -q
```

The generator preserves a backup of an existing CSV. Training preserves the old
model as an ignored .pkl backup. Source/data hashes, realized telemetry rates and
configuration are recorded in data/raw/module_a_transactions.metadata.json and
ml/models/module_a.metrics.json. Changing source data requires regeneration.
A fresh clone/build needs the authorized source, or the generated CSV plus its
metadata; there is no fallback to fabricated financial data.

The predictor and six-feature input contract are unchanged. For explicit device
novelty use the existing is_new_device field. device_counts is empty because this
source does not provide the deployment's device history; the existing device_id
fallback therefore treats any supplied ID as unfamiliar. The existing API may not
expose explicit novelty; that limitation is not resolved in this phase. Runtime
clock time and manually supplied velocity differ from training proxies. Restart
an already-running backend to clear its model cache after retraining.

Old handpicked amount-boundary demos are invalid. Phase 3 updated Module D
regression expectations using the current model outputs, without changing Module A.

## Module D synthetic joint data

See [Module D datasheet](MODULE_D_DATASHEET.md): actual module outputs are paired
synthetically with explicitly derived OR-policy labels. Its metrics are not
real-world performance. The Android companion adds an optional real phone report
at inference; it does not change the synthetic telemetry in Module A training.
