# Module D: learned synthetic scenario policy

The three inputs are actual scores from the existing trained A/B/C artifacts.
No jointly observed, labeled transaction + URL + message incident dataset exists
in this checkout. All 2,000 pairings and all `combined_label` values are synthetic.
The label is 1 iff at least one PRESENT component has a positive source label
(A fraud, B phishing, C a non-none signature). This OR policy fits an evidence
triage demo; it does not establish that components belong to one fraud incident.
No external source validates this labeling policy or the sampled prevalence.

A/B components come from their base-model held-out pools. C scores use its fitted
model plus rules on in-sample source texts; this optimistic contamination is not
an independent stacked-model evaluation. C positive sampling is dominated by greed
and does not validate fear coverage. A source rows contain synthetic call/device
flags; C labels are weak/manual. B uses historical real URLs. Components are paired
independently; real cross-channel dependence and B URL folding within C are not modeled.

Each component/class pool is split before pairing, with disjoint source IDs in
D train/test. Source text/domain/campaign dependence can remain. Each split samples
at most 160 source components per module/class; reuse creates dependent scenarios.
Seed 42, 1,600 train / 400 test; test has 262 positive and 138 negative labels.
Presence masks 1 to 7 are uniformly sampled; absent scores are zero. The model cannot
distinguish missing from an observed zero score. This is the same policy at inference.

## Fit and evaluation

Unscaled LogisticRegression C=1, max_iter=1000. Threshold 0.5; tier cutoffs remain
0.25/0.50/0.75, without deployment calibration. Test precision/recall/F1 **0.8855**,
FPR **0.2174**, confusion TN=108, FP=30, FN=30, TP=232. Not suspiciously perfect.
**Do not present these metrics as real-world performance.**

| Parameter | Full fit | Five-fold training spread (min to max) |
| --- | ---: | ---: |
| A score | 4.8799 | 4.5617 to 4.7780 |
| B score | 7.1789 | 6.6877 to 6.8830 |
| C score | 5.8928 | 5.5563 to 5.6256 |
| Intercept | -2.6440 | -2.5407 to -2.4860 |

These are descriptive coefficient ranges, not confidence intervals. Folds train on
80% of D training rows, so their regularized estimates differ from the full fit.
Repeated components make folds dependent. Coefficients are log-odds slopes, not
normalized importance shares. Exact linear SHAP relative to all-zero inputs is
`coefficient * score`; intercept plus contributions reconstructs the logit. This
reference is mathematical, not an average legitimate transaction. Headline modules
are ordered by their actual positive log-odds contributions. Per-module SHAP or
heuristic reasons remain separately identified; they are not causal explanations.

Missing model file: warning + original checkout weights A=.45, B=.25, C=.30,
renormalized over submitted modules. Corrupt/incompatible artifacts raise errors.
A benign-looking demo now scores High; the modest transaction alone scores Medium,
and with the fear demo it scores Critical. Tests record these outcomes, not a
claim that the model correctly recognizes fraud.

## Reproduction

Use the backend venv with the existing A/B/C datasets and artifacts:

```powershell
.\backend\venv\Scripts\python.exe ml/generate_module_d_data.py
.\backend\venv\Scripts\python.exe ml/train_module_d.py
.\backend\venv\Scripts\python.exe -m pytest tests -q
```

CSV and provenance JSON: `data/raw/module_d_scenarios.*`; model:
`ml/models/module_d.pkl`; tracked report: `ml/models/module_d.metrics.json`.
The report records artifact/data SHA-256 and exact coefficient folds. Base scores
must be regenerated and D retrained when A/B/C change. Source datasets/models remain
gitignored; this is not automatically reproducible from a data-free clone.
