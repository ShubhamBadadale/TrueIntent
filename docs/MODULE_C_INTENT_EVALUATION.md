# Module C intent experiment

This change improves provenance, leakage controls and Unicode text handling, and
adds a small diagnostic taxonomy experiment. **It does not establish reliable
digital-arrest detection or reliable Hindi/Hinglish scam detection.** The selected
word+character model has binary detection gains on this dataset, but detailed
intent recognition remains weak. Do not present authored-example results as real
scam recall.

## Sources and labels

Windows security blocked reading the downloaded Kaggle fraudulent-email archive
as containing a virus or potentially unwanted software. That block was not
bypassed. The experiment explicitly excludes the archive with `--skip-emails`.
The old 7,696-row experiment cannot be exactly reproduced with this source subset.

| Provenance | Rows | Meaning |
|---|---:|---|
| real_public | 4,602 | Existing UCI SMS: 4,501 ham and 101 prize-selected spam |
| manually_curated | 5 | Existing cited victim/report excerpts; contextual labels, not full transcripts |
| synthetic | 54 | AI-authored English illustrations, six seeds per requested category |
| augmented | 63 | 54 Hinglish and 9 Hindi adaptations of those seeds; synthetic origin retained |

Total: 4,724 rows. All 117 authored/adapted rows have `origin=synthetic`. A
translation bundle receives total sample weight one, rather than counting as two
or three independent seeds. No thousands of generated examples, oversampling or
undocumented text translations are used. The new authored examples have not been
independently human reviewed.

Source references and prior license details remain in `data/MODULE_C_DATASHEET.md`
and `data/module_c_fear_sources.json`. The UCI archive hash is
`1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3`.
The SMS/excerpt CSV hash is
`f27894e7b48e1eb0cafee2fb9a7ea437940e91a7314027876dabdd2ec6d67511`.
The metrics JSON records source and authored-seed hashes. Each row retains source,
label basis, language, provenance, origin, seed ID and leakage group.

The primary intent taxonomy uses one label per example. Real scams can overlap;
this is a pragmatic single-label experiment, not a claim of mutually exclusive
behaviors. Annotate the most specific requested action/context:

| Label | Definition / boundary |
|---|---|
| benign | Ordinary conversation or legitimate/advisory language; scam words alone do not establish intent |
| urgency_pressure | Coercive payment deadline or isolation without a more specific tactic; ordinary deadlines are benign |
| authority_fear | Threat, accusation or official coercion without explicit remote detention |
| digital_arrest | Claimed remote custody/detention or continuous monitored video interrogation and isolation |
| investment_scam | Investment/return claims, trading schemes or withdrawal-fee traps |
| kyc_upi_scam | Account-verification pretexts or misuse of QR, collect requests and UPI payment flows |
| impersonation | Claimed familiar/trusted identity to obtain payment, without a more specific context |
| courier_customs_scam | Parcel, delivery or customs pretext; explicit remote detention takes precedence |
| credential_theft | Password, recovery phrase or authentication-secret collection outside the specific KYC/UPI context |
| other_fraud | Historical weak prize/advance-fee category; never silently relabeled investment scam |

The five existing authority labels are retained with their historical contextual
annotation caveat. None supplies a separate real digital-arrest class. Most new
classes have only six authored seeds, each with linked language variants.

## Models, preprocessing and evaluation

Baseline: the existing word TF-IDF 1–2 grams, 10,000 features, balanced logistic
regression. Candidate: word TF-IDF plus character-within-word 3–5 grams (15,000
character features), sublinear TF and balanced logistic regression. Both candidates
use the same dataset, grouped folds and per-seed sample weights.

Candidate preprocessing is serialized with the model: Unicode NFKC, case folding,
whitespace cleanup and removal of zero-width formatting characters. URLs/emails
are replaced with markers in text features. Negations are preserved. Word
tokenization keeps Devanagari vowel marks; character features can share fragments
across spelling variations but do not perform semantic translation/transliteration.
Module B URL analysis remains a separate inference channel and is excluded from
these text-classifier metrics. The OCR sufficiency check now accepts Unicode
letters; this does not install Hindi Tesseract language data or establish OCR accuracy.

Five StratifiedGroupKFold folds use seed 42. Connected components join explicit
translation lineage, normalized contact/number templates and text pairs with
word-TFIDF cosine similarity at least 0.90. There are 4,613 groups and 60 near-text
edges. No seed or connected group crosses a fold. The all-text similarity
representation only constructs groups; model vocabularies/IDF fit on training
folds. This heuristic cannot guarantee detection of all semantic/campaign clones.

Candidate selection uses exploratory cross-validation: retain word+character
features if public-slice binary F1 falls by no more than 0.005 and authored-slice
macro-F1 increases. Both conditions passed. There is no untouched final test,
significance test or production performance claim. Final models refit all rows.
The stored per-row OOF file allows inspection of every heldout prediction.

`macro_f1` averages all ten labels, including unsupported labels in a slice.
`supported_label_macro_f1` additionally reports the average over labels present
in that slice. Zero-support class recall is **unmeasurable**, not zero real-world
recall. Binary metrics use `1-P(benign) >= 0.5`, matching the inference text score;
multiclass metrics use argmax. These are different decisions and the score is not
a calibrated real-world fraud probability.

## Old and new results

| Experiment | Labels / rows | Macro precision | Macro recall | Macro-F1 |
|---|---|---:|---:|---:|
| Previously tracked result | 3 / 7,696, including emails | 0.6623 | 0.6614 | 0.6618 |
| Legacy pipeline re-run on available public subset | 3 / 4,607, no emails | 0.6659 | 0.6469 | 0.6561 |
| Word baseline on expanded data | 10 / 4,724 | 0.3962 | 0.2965 | 0.3205 |
| Selected word+character model on expanded data | 10 / 4,724 | 0.3833 | 0.2963 | 0.3264 |

The three-label and ten-label macro scores are **not directly comparable**.
The valid feature comparison is word versus word+character on the same expanded
dataset and folds. The old dataset's near-perfect majority-class metrics masked
authority/fear recall of 0/5. The subset legacy rerun also has authority recall 0/5.

| Slice | Word binary P / R / F1 | Word+character binary P / R / F1 |
|---|---|---|
| All rows | .7190 / .9381 / .8140 | .8848 / .9143 / .8993 |
| Public only | .5976 / .9245 / .7259 | .8716 / .8962 / .8837 |
| Authored only | .9000 / .9519 / .9252 | .8981 / .9327 / .9151 |
| Hinglish (54 authored) | .8889 / 1.0000 / .9412 | .8889 / 1.0000 / .9412 |

Recall fell while precision improved overall and on the public slice. Authored
binary F1 fell. All six Hinglish benign examples are false positives at the binary
threshold: the high Hinglish binary F1 is misleading without class counts. Argmax
Hinglish macro-F1 over ten labels is only .1967 → .2129. Hindi macro-F1 is .0250 →
.0667 on just nine authored examples, one per requested category; this is nowhere
near enough support for a language-performance conclusion.

Selected model pooled per-class performance:

| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| benign | .9869 | .9984 | .9926 | 4,514 |
| urgency_pressure | .2222 | .1538 | .1818 | 13 |
| authority_fear | .2000 | .1111 | .1429 | 18 |
| digital_arrest | .2000 | .0769 | .1111 | 13 |
| investment_scam | .2000 | .0769 | .1111 | 13 |
| kyc_upi_scam | .7143 | .3846 | .5000 | 13 |
| impersonation | .1667 | .1538 | .1600 | 13 |
| courier_customs_scam | .0000 | .0000 | .0000 | 13 |
| credential_theft | .1429 | .0769 | .1000 | 13 |
| other_fraud | 1.0000 | .9307 | .9641 | 101 |

Public authority recall is **1/5 for both feature configurations**. Pooled authority
recall is 1/18 → 2/18 and authored digital-arrest recall is 0/13 → 1/13. These tiny
counts do not establish reliable detection. No real digital-arrest or real
Hindi/Hinglish recall is measurable in this experiment. KYC/UPI recall regressed
from .5385 to .3846; courier/customs recall remains zero.

Confusion matrix: rows actual, columns predicted, in the table order above.

```text
4507 0 0 0 1 0 2 1 3 0
   8 2 0 1 0 0 1 0 1 0
   6 0 2 1 1 0 2 6 0 0
   6 3 3 1 0 0 0 0 0 0
   8 1 0 0 1 0 2 0 1 0
   7 0 0 0 0 5 0 0 1 0
   5 3 2 0 0 0 2 1 0 0
   4 0 3 2 1 0 3 0 0 0
   9 0 0 0 1 2 0 0 1 0
   7 0 0 0 0 0 0 0 0 94
```

Both candidates' complete per-class reports, confusion matrices and language/
provenance slices are in `ml/models/module_c.metrics.json`.

## Keyword rules and inference

The previous fixed substring lists could override the classifier and alter its
score without a measured benefit, including on scam advisories and quoted text.
The evaluation now tests rule candidates using training-fold support from at least
two distinct groups and precision >=.90 for a specific intent. Translations do not
count as independent support. **No rule qualified in any fold.** The filtered-rule
ablation therefore equals ML-only predictions; no keyword override or score blend
is retained. This supports removing unvalidated overrides, not a claim that all
possible rules are useless. The original lists remain only as evaluation candidates.

Inference exposes `intent`, `intent_probabilities`, `rule_evidence` and
`text_assessed` alongside existing fields. Reasons identify ML predictions
explicitly; any future retained rule evidence has `affects_score=false`.
The legacy psychology `signature` is supplied by a separate lightweight
three-class compatibility classifier, so Module D's existing interface and token
attribution can still operate. It is not the expanded intent label or a separate
validated performance claim. Both fitted classifiers total about 4.4 MB on disk.

Missing or invalid text models abstain. API paths consuming Module C return 503
instead of presenting a zero placeholder as low risk. The direct library envelope
sets `text_assessed=false`; direct consumers must respect that flag. The existing
Module B URL folding still applies to successful text analysis. No changes were
made to the implementations of Modules A, B or D.

## Remaining weaknesses and next practical step

The principal bottleneck is independently reviewed real examples for rare intents,
especially benign near-matches, modern authority coercion and Hindi/Hinglish. The
small authored supplement does not solve that shortage. Source/selection bias
remains: benign SMS versus prize-selected spam, contextual news fragments versus
messages, and a single author's style. Label overlap and contextual ambiguity
remain. Scores and thresholds lack calibration against deployment prevalence.
Priority should be a modest reviewed, consented/anonymized real challenge set with
incident IDs and language tags, rather than more variations of these same seeds.

## Reproduction and files

```powershell
.\.venv\Scripts\python.exe -m ml.generate_module_c_data --skip-emails
.\.venv\Scripts\python.exe -m ml.train_module_c
.\.venv\Scripts\python.exe -m pytest tests/test_module_c.py tests/test_module_c_classifier.py tests/test_module_c_intents.py tests/test_module_c_ocr.py tests/backend/test_api.py tests/test_integration.py -q
```

Verification: **42 passed, 2 skipped** (real screenshot/Tesseract coverage), with
two existing Starlette/AnyIO deprecation warnings. Regression tests cover
Devanagari text, negation preservation, seed/translation isolation, independent
rule support, ML/rule separation and API abstention. No test-fixture accuracy is
reported as model performance.

Files changed for this task:

- `data/module_c_intent_seeds.json`, `data/MODULE_C_DATASHEET.md`
- `ml/features_module_c.py`, `ml/module_c_dataset.py`, `ml/evaluate_module_c.py`
- `ml/generate_module_c_data.py`, `ml/train_module_c.py`, `ml/predict_module_c.py`, `ml/ocr_module_c.py`
- `ml/models/module_c.metrics.json`
- Module C fields/handling in `backend/app/schemas.py` and `backend/app/main.py`
- `tests/test_module_c.py`, `tests/test_module_c_classifier.py`, `tests/test_module_c_intents.py`
- This report

Generated local outputs include `ml/models/module_c.pkl`, the source metadata,
`data/raw/module_c_intent_oof.csv` and the three-class subset reproduction artifact
and metrics. Raw datasets and joblib models remain gitignored. Existing unrelated
worktree changes from earlier tasks are preserved.
