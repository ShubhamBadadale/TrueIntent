# Module C data and evaluation (Phase 4)

**Historical report.** The current intent experiment and source exclusion are
documented in [MODULE_C_INTENT_EVALUATION.md](../docs/MODULE_C_INTENT_EVALUATION.md).
The figures and keyword fallback described below refer to the older artifact;
they do not describe the current ten-intent classifier.

**Fear/authority recognition is not validated: out-of-fold recall is 0/5.**
This phase activates a text classifier, but does not establish a successful learned
replacement for fear/authority detection. Existing keyword safeguards are retained.
Data coverage is substantially weaker than the financial/URL sources used for A/B.

## Sources and access

- Almeida and Hidalgo, [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection),
  DOI 10.24432/C5CC84, CC BY 4.0. Public ZIP downloaded successfully. The UCI page
  describes this as a historical SMS spam/ham corpus, not a behavioral-signature set.
- Rachael Tatman, [Fraudulent E-mail Corpus](https://www.kaggle.com/datasets/rtatman/fraudulent-email-corpus),
  Kaggle version 1, CC BY-SA 4.0, public and downloaded without authentication.
  The archive contains `fradulent_emails.txt` (original spelling), in mbox format.
  Bodies are parsed; headers/subjects/addresses in headers are not model features.
- Five short excerpts from five separate reported incidents. Exact text, individual
  citations, dates, source type and labeling rationale are in
  [module_c_fear_sources.json](module_c_fear_sources.json). One is a reported caller
  quotation; four are victim-reported speech/complaint or reporter fragments.
  **These are not five full or independently verified call transcripts.** No
  reconstructed dialogue, translated inventions or synthetic padding was added.
  Each news source contributes no more than 25 quoted words. These excerpts retain
  their source rights; the entire assembled dataset is not claimed to have one
  blanket open license. Preserve attribution and the email corpus share-alike terms.

Current source checks did not show either corpus becoming private. The pre-existing
local SMS CSV was not modified or trusted as the source: the original UCI ZIP was
used directly. The unrelated synthetic signature generator in ml/scripts was not run.

## Label provenance and coverage

Output: `data/raw/signature_examples.csv`, with `text,signature` as expected by the
trainer plus `source_url,source_id,source_kind,label_basis,group_id` audit columns.

| Class | Rows | Label origin |
|---|---:|---|
| none | 4,501 | Source ham mapped to none; not all possible benign language |
| greed_opportunity | 3,190 | 3,089 real 419-email bodies plus 101 real SMS; weak behavioral labels |
| fear_authority | 5 | Manual contextual annotation of cited reported incident excerpts |

The email corpus label is mapped to greed at corpus level, not individually reviewed.
Some emails can contain other tactics; this mapping is noisy. SMS greed selection
requires source spam AND prize/winner/won/lottery/awarded/cash-reward wording.
605 other spam rows are excluded, not mislabeled as legitimate or fear. The
source spam label is not proof that every prize promotion is financial fraud.
No behavior labels were obtained from the existing predictor's keyword lists.

After whitespace normalization and grouping text with number/contact variations,
1,114 duplicate groups' extra rows were removed. This also removes some semantically
distinct messages with identical normalized templates; it is a conservative leakage
control, not a complete near-duplicate/campaign detector. No oversampled or synthetic
rows were used. Class weighting compensates numerically for imbalance but cannot
supply the missing fear-language diversity. Invented unit-test fixtures never enter
production training or the reported evaluation.

## Evaluation

TF-IDF word 1-2 grams (10,000 features) and Logistic Regression, balanced class
weights, seed 42. Five stratified folds after group deduplication: each of the five
fear excerpts is held out once, leaving only four for its fold's training. TF-IDF is
fit separately inside each fold. Metrics below pool the out-of-fold predictions;
final artifact is then refit on all rows. There is no train-set fallback evaluation.

| Class | Precision | Recall | F1 | OOF support |
|---|---:|---:|---:|---:|
| fear_authority | 0.0000 | 0.0000 | 0.0000 | 5 |
| greed_opportunity | 0.9984 | 0.9853 | 0.9918 | 3,190 |
| none | 0.9886 | 0.9989 | 0.9937 | 4,501 |

Macro F1: **0.6618**. Accuracy 0.9926 hides total failure on the rare fear class.
The near-perfect greed/ham figures are suspiciously optimistic as deployment
estimates: long historical emails and short conversational SMS have strong source
and style differences; SMS greed evaluation uses the same weak labeling criterion
as training, and residual campaign similarities may remain. There is no separate
benign email corpus, independent behavioral gold set, temporal or source-disjoint
holdout. Do not present these metrics as real-world performance. The five fear
cases cannot support a stable estimate of real fear/authority recall.

Language coverage is principally English text. Hindi/Hinglish, regional languages,
calm coercion, genuine law-enforcement messages, advisory text quoting scams, modern
investment scams and OCR noise are inadequately represented. An advisory or victim
narrative may be incorrectly classified as a scam message. No OCR accuracy claim.

## Runtime and reproduction

The established 50/50 keyword/ML score blend and keyword signature safeguard remain
when keywords match. Without keywords, the classifier supplies signature and score.
Embedded URLs still feed the existing Module B folding path. Thus the metrics above
measure the classifier alone, not the runtime blend. Missing/failed artifacts retain
the keyword fallback. Status explicitly says `fear_authority unvalidated` when active.

```powershell
.\backend\venv\Scripts\python.exe ml/generate_module_c_data.py
.\backend\venv\Scripts\python.exe ml/train_module_c.py
.\backend\venv\Scripts\python.exe -m pytest tests/test_module_c.py tests/test_module_c_classifier.py tests/test_module_c_ocr.py -q
```

Generator downloads source ZIPs if missing; cached ZIPs support offline reproduction.
It backs up any existing signature CSV, validates sources/labels and writes a metadata
sidecar with SHA-256 hashes and counts. The trainer verifies the hash before fitting.
Metrics/fold reports: `ml/models/module_c.metrics.json`; per-example OOF predictions:
`data/raw/module_c_oof_predictions.csv`. Raw data and `.pkl` artifacts remain ignored.
Restart the backend after training to clear cached models. Train with the backend's
Python environment to match its scikit-learn version.

Phase 3 remains pending: this classifier's existence does not resolve its fear
coverage failure or the absence of independent combined-case labels. Phase 5 is
not implemented.

## Verification result

Backend-environment full suite: 63 passed, 2 skipped, 3 failed. Module C-focused
suite: 18 passed, 2 OCR engine tests skipped. The full-suite failures are unchanged
Module D Low/Critical demo expectations and the integration test's assumption that
the modest transaction scores Low under Module A (it now scores High). These
expectations remain for the authorized Phase 3 work; A, B and D were not edited in
this phase. Existing Module B model-version warnings also remain outside this scope.
