# Module B: offline URL evaluation

The production model remains character TF-IDF (3–5 grams, 10,000 features) plus
logistic regression. Engineered-only and combined models are retained as
reproducible comparison candidates. There is no established general improvement
from adding the engineered features. The inference response still contains
`score`, `reasons`, and `ml_status`, with the existing 50/50 classifier/rules blend.

## Data and audit

The user approved downloading the existing repository source: Kaggle **Web page
Phishing Detection Dataset**, version 2, by Hannousse and Yahiouche, collected in
May 2020. Attribution and licensing are in `data/README.md`. The importer selects
raw URLs and provided labels; no numeric upstream features or synthetic training
labels are used. No listed URL is visited.

- Source: 11,430 rows; ingestion removes 3 repeated lowercase URL texts.
- Training CSV: 11,427 rows, 5,715 legitimate and 5,712 phishing; no remaining
  duplicates under the baseline's lowercase text representation.
- CSV SHA-256: `588f85c75146706a255e8001738b75323443cd062a3c19896df24a999428374f`.
- The random holdout has 452 shared hostnames (805 test rows) and 488 shared
  registered domains (1,133 test rows). Nearly half of its test rows therefore
  have a registered domain seen during training.
- A conservative near-duplicate heuristic identifies 988 rows in repeated
  within-host templates. The random split shares 142 templates, affecting 179
  test rows. It ignores scheme, fragment and query values, decodes/lowercases the
  path, and collapses digit runs. These are possible related examples, not proven
  equivalent resources. Arbitrary cross-domain campaign clones are not detected.
- The domain holdout has zero shared hostnames, registered domains or templates
  under that heuristic: 9,116 training rows and 2,311 test rows.

## Preprocessing and lightweight features

Text preprocessing is shared inside saved pipelines and at inference: trim outer
whitespace, then the original vectorizer lowercases character text. It preserves
paths, queries and encoding for the baseline. The old baseline already applied
equivalent trimming/lowercasing; no previously absent mismatch is claimed.

The numeric branch parses HTTP(S) URLs, assumes HTTP for schemeless input, and
normalizes hostname case and IDNA for structural features. The same transformer
is fitted and serialized with the classifier. StandardScaler and TF-IDF learn
only from each training partition. No URL feature cache is used in the final
latency measurement or serving code.

Fourteen scalar features cover URL/hostname/path lengths, subdomain count, digit
and special-character ratios, character entropy, valid IPv4/IPv6 hosts, IDN or
punycode hosts, counts of a fixed suspicious-keyword list and percent-encoded
bytes, hyphen count, three-or-more hostname hyphens, and membership in a small
fixed URL-shortener list. These are learned covariates, not proof of phishing.

`tldextract==5.3.0` uses its bundled Public Suffix List, with downloads and disk
cache disabled. ICANN eTLD+1 groups all tenants of private hosting services
together (e.g. blogspot.com). This is deliberately conservative. Unknown suffixes
fall back to the full hostname, and IP literals form their own groups. New
suffixes and aliases may therefore require a future PSL/dependency update.

Inference also uses shared hostname parsing: uppercase HTTPS is recognized;
credentials cannot hide an IP host; IPv6 is recognized. Live page fetching is
disabled by default. The existing explicitly opt-in live inspection code is not
part of the model or evaluation.

## Evaluation design

All three candidates use the same rows within each split and threshold 0.5.
Random evaluation reproduces the old 80/20 stratified seed-42 split. The stricter
holdout uses registered-domain groups: from 100 deterministic seed-42
GroupShuffleSplit candidates, choose the split closest to 20% of rows and overall
class prevalence. This balancing uses labels only, never model scores.

Five grouped validation folds within the outer domain-training partition compare
model families. The conservative deployment policy retains TF-IDF unless the
mean validation F1 gain reaches 0.01. This is an engineering preference, **not** a
statistical significance test or a preregistered experiment. The heldout test
results are reported for all candidates, regardless of which is selected.

After evaluation, the selected pipeline is refitted on all validated rows.
Reported holdout metrics refer to separate evaluation fits, not unseen examples
for that final full-data artifact. Historical examples in integration tests check
wiring, not generalization accuracy.

The complete measured results, confusion matrices, grouped validation fold scores
and environment are in `ml/models/module_b.metrics.json`. PR-AUC is average
precision. Batch latency is elapsed prediction time divided by heldout rows;
single-URL latency summarizes the first 200 heldout URLs scored individually.
Both include preprocessing and exclude API transport, artifact loading and rules.

## Reproduce

Final measurements in this environment (single-URL median latency):

| Split | Model | Precision | Recall | F1 | ROC-AUC | PR-AUC (AP) | ms/URL |
|---|---|---:|---:|---:|---:|---:|---:|
| Random | TF-IDF baseline | 0.9173 | 0.9020 | 0.9096 | 0.9711 | 0.9752 | 1.820 |
| Random | Engineered | 0.7703 | 0.6308 | 0.6936 | 0.7982 | 0.8274 | 0.439 |
| Random | Combined | 0.9284 | 0.8968 | 0.9123 | 0.9716 | 0.9740 | 3.392 |
| Domain disjoint | TF-IDF baseline | 0.8624 | 0.9281 | 0.8941 | 0.9618 | 0.9644 | 1.596 |
| Domain disjoint | Engineered | 0.7884 | 0.7160 | 0.7505 | 0.8425 | 0.8759 | 1.224 |
| Domain disjoint | Combined | 0.8774 | 0.9108 | 0.8938 | 0.9624 | 0.9661 | 2.023 |

Grouped validation mean F1: TF-IDF 0.8850, engineered 0.6741, combined 0.8936.
Combined improves precision but reduces recall on both holdouts. Its modest
random F1 gain does not persist on the domain holdout. No overall improvement or
statistically significant difference is claimed. Single-run timings are subject
to machine load; batch and p95 values are also recorded in the JSON.

Verification: 42 focused Module B, backend API and integration tests passed, with
two existing Starlette/AnyIO deprecation warnings. Regressions cover feature
semantics, IP/credential parsing, offline defaults, PSL behavior, serialization,
response shape and leakage report fields.

Files changed for this task: `ml/features_module_b.py`, `ml/train_module_b.py`,
`ml/predict_module_b.py`, `ml/models/module_b.metrics.json`,
`backend/requirements.txt`, `tests/test_module_b_classifier.py`, and this report.
Generated local files: `data/raw/module_b_urls.csv`, its `.metadata.json`, and
`ml/models/module_b.pkl`. Earlier work on other modules is separate from this task.

From the repository root, install `backend/requirements.txt`, then run:

```powershell
.\.venv\Scripts\python.exe -m ml.generate_module_b_data
.\.venv\Scripts\python.exe -m ml.train_module_b
.\.venv\Scripts\python.exe -m pytest tests/test_module_b.py tests/test_module_b_classifier.py tests/backend/test_api.py tests/test_integration.py -q
```

The CSV, its provenance metadata and the joblib model are generated locally and
ignored by Git. The metrics JSON and this report are reviewable tracked output.

## Limits

This is a single, balanced, historical collection; it does not measure today's
phishing prevalence, new campaigns, geographic/language coverage or temporal
drift. Domain isolation reduces one important leakage channel but does not
guarantee campaign isolation. Unknown suffixes and cross-domain near duplicates
remain limitations. The snapshot lacks timestamps suitable for a temporal test.
Lowercase deduplication matches TF-IDF's representation, although URL paths can
be case-sensitive on real servers.

The old tracked random-split baseline reported precision 0.917333, recall
0.902887 and F1 0.910053. Re-running the unchanged baseline here produced precision
0.917260, recall 0.902012 and F1 0.909572 (one more false negative). The cause of
that small reproducibility difference has not been established; comparisons use
the fresh baseline from this environment.

These classifier results do not validate the existing rule weights, 50/50 blend,
frontend risk tiers or Module D fusion. Rule reasons explain heuristic matches,
not individual learned feature contributions. The optional live fetch remains
outside this offline evaluation. No changes to Modules A, C or D are required by
this work.
