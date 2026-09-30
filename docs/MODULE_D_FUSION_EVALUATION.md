# Module D fusion experiment

**This evaluates synthetic policy recovery, not real-world fraud detection.**
No linked, adjudicated transaction/message/URL/call dataset is available.

## Audit of the existing approach

The old generator's label is exactly OR of the source labels of PRESENT components.
Thus it primarily learns whether any source component is positive. This is not
literally OR over thresholded detector scores, which can disagree with labels.
There is no label evidence that channels belong to one incident or corroborate
each other. The old model has only three score features, conflates missing with
observed zero, uses in-sample C predictions and independently pairs components.
Repeated training components make its row-level coefficient folds dependent.
C also already includes URL risk, which can duplicate B evidence in fusion.

The historical precision/recall/F1 .8855 belong to that old OR task. They are not
directly comparable to the new policy below. Legacy generator/trainer functions
remain available by explicit name; their unsupported Module A path stays blocked.

## Features and serving contract

Training and inference share `ml/features_module_d.py`:

- A, B, C scores and three presence flags.
- Active-call and call-known flags: omitted and reported false differ.
- Credential-request and authority/fear probabilities supplied by C.
- Message score × A score; active call × A score; B score × credential signal;
  authority/fear signal × A score.

Absent channels gate their related interactions to zero. All-absent and call-only
inputs are rejected. Scores must be finite and within [0,1]. C now exposes its
existing text and embedded-URL scores. D uses C text risk separately and the max
of explicit/embedded URL risk for B, counting URL evidence once. Legacy C results
without decomposition retain an explicit warning that URL evidence may overlap.
Tactic probabilities are model signals, not confirmed requests or established facts.

The backend accepts optional strict Boolean `active_call`. The frontend sends
known Yes/No values and identifies them as user reports, not verified telemetry.
Transaction details remain display-only. **Live transaction fusion is still
disabled:** Module A is an IEEE-CIS source-unit benchmark, not a validated INR
risk detector. A-related experiments below are offline only.

## Synthetic data and evaluation

Seed 42 generates 600 independent synthetic families: 300 training, 100 validation,
200 test. Latent anomaly, phishing, manipulation, call and tactic indicators are
drawn at fixed declared probabilities in the generator. Observed scores are
Beta(6,2) or Beta(2,6) draws conditional on simulated signals. Labels implement:

```text
severe A/B/C evidence
OR unusual transaction AND (manipulative message OR active call OR authority pressure)
OR phishing link AND credential request
```

This is another invented policy, not ground-truth fraud. The labels agree with
the full latent-component OR rule on 73.17% of rows. The 26.83% differences are
designed policy distinctions, not discoveries about real fraud.

Each ablation retains the same 200 test families and original incident labels.
Hiding channels never rewrites labels. Availability variants stay within one
split; zero family IDs overlap across splits. The serving model learns eight
masks per training family: 2,400 training rows but only 300 independent families.
All signals, calls, detector errors and relationships here are simulated; no base
model is retrained or assumed to produce these distributions in practice.

Comparators: original three-score LogisticRegression; simple rule
`min(1, .7*max_score + .3*max_interaction)`; 14-feature LogisticRegression (C=1);
HistGradientBoostingClassifier (80 iterations, seven leaves, L2=2). Threshold .5
is fixed. Validation results are recorded separately. LR is retained as the simple
serving contract with exact coefficient explanations; GB is not automatically
promoted on synthetic results. No untouched real-data evaluation exists.

## Results

Test F1, **separate models retrained per input subset**:

| Inputs | Existing three-score LR | Simple rule | Interaction LR | Gradient boosting |
|---|---:|---:|---:|---:|
| A | .7418 | .6067 | .7418 | .7308 |
| B | .6273 | .4471 | .6273 | .6446 |
| C | .6608 | .4859 | .6400 | .5740 |
| A+B | .7580 | .7349 | .7580 | .8117 |
| A+C | .7512 | .7778 | .7944 | .7383 |
| B+C | .7227 | .7018 | .6514 | .6210 |
| A+B+C | .8070 | .8137 | .8073 | .8037 |
| A+B+C+call | .8070 | .8209 | .8246 | .8000 |

Full-input details:

| Approach | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|
| Existing approach | .8440 | .7731 | .8070 | .8580 | .9049 |
| Simple rule | .7383 | .9244 | .8209 | .8745 | .9179 |
| Interaction LR | .8624 | .7899 | .8246 | .8808 | .9207 |
| Gradient boosting | .8713 | .7395 | .8000 | .8636 | .9075 |

The interaction gain is modest and inconsistent: **B+C and C regress**. Boosting
helps A+B here but is not generally better. No statistical significance or
real-world accuracy gain is established.

The actual serving artifact is one LR trained across all masks, not eight routed
models. Its F1 is .8174 with A+B+C+call and .6849 with B+C. Corresponding
precision/recall: .8468/.7899 and .7500/.6303. Do not present the ablation's .8246
as serving-model accuracy. **This is not evidence of improved accuracy for the
currently available live B+C workflow.** Operational changes are explicit
availability, URL evidence separation and inspectable interactions.

`ml/models/module_d.metrics.json` contains all validation/holdout metrics,
confusion matrices, feature definitions and source hash. Test support is fixed at
119 positive and 81 negative simulated incidents. The generated CSV explicitly
marks every row `synthetic_policy` and records its label basis.

## Compatibility and limitations

The response retains `tier`, `score`, `explanation`, `details`. Version-1 artifacts
remain readable. Missing files retain the old weighted fallback; corrupt or
incompatible artifacts fail visibly. Existing tier thresholds .25/.5/.75 remain
uncalibrated policy thresholds. Version-2 results explicitly say synthetic-policy
risk index, not calibrated fraud probability.

Coefficient × engineered-feature contributions plus the intercept reconstruct
the logit. They are not causal effects or normalized importance. Interaction
contributions are reported separately rather than independently counted for both
constituent modules. Missing channels are named as skipped. Restart a running
backend to load the changed Python code.

Limitations include invented prevalence and score noise, no real linked incidents,
independently simulated inputs, one seed and a small test set, weak C tactic
coverage, unavailable operational A risk, and no real-data calibration. Call-only
evidence cannot produce a verdict. Better synthetic-policy fit is not evidence
that an interaction is useful on real fraud. The next evidence requirement is a
small reviewed incident set with channel availability and incident IDs.

## Reproduction and changed files

```powershell
.\.venv\Scripts\python.exe -m ml.generate_module_d_data
.\.venv\Scripts\python.exe -m ml.train_module_d
.\.venv\Scripts\python.exe -m pytest tests/test_module_d.py tests/test_module_d_learned.py tests/test_module_d_interactions.py tests/test_integration.py tests/backend/test_api.py tests/test_module_c_intents.py -q
```

The current trainer regenerates the deterministic simulation; it does not import
real incident data. CSV/model artifacts are gitignored; metrics are tracked.

- `ml/features_module_d.py`, `ml/evaluate_module_d.py`
- `ml/generate_module_d_data.py`, `ml/train_module_d.py`, `ml/predict_module_d.py`
- `ml/models/module_d.metrics.json`
- `ml/predict_module_c.py`: expose existing score components only
- `backend/app/schemas.py`, `backend/app/main.py`: optional call status
- `frontend/src/combinedAnalysis.js`, `frontend/src/components/CombinedCheck.jsx`,
  `frontend/src/components/CombinedResults.jsx`, `frontend/tests/combined.test.mjs`
- `tests/test_module_d_interactions.py`, `data/MODULE_D_DATASHEET.md`, this report

Verification: **46 backend/ML tests and 12 frontend tests passed; frontend build
passed**. A non-fatal Windows Vite temporary-cache cleanup warning appeared;
backend warnings were existing Starlette/AnyIO deprecations. No A/B/C model was
retrained for this task. Earlier unrelated worktree changes remain untouched.
