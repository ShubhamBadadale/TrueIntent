# TrueIntent — Dataset Sourcing & Usage Documentation

This directory contains datasets used for training and evaluating the ML modules of the TrueIntent fraud intent verification system.

---

> **Module A is now hybrid: real IEEE-CIS financial observations plus synthetic call/device flags.**

The six-feature contract is unchanged. `amount` is real; `hour_of_day`, `is_odd_hour`
and `transaction_velocity` are documented proxies derived from real observations.
`is_active_call` and `is_new_device` are simulated for every row, with configurable
hypothetical priors and independent 12.5% bit flips. Labels remain real and unchanged.
**Do not present these metrics as real-world performance.** See [Module A datasheet](DATASHEET.md)
for definitions, source choice, noise, full metrics, ablation, and reproduction commands.

---

## Dataset Sourcing Overview across Modules

| Module | Dataset File Path | Status (as of 2026-09-26) | Sourcing & Methodological Notes |
| :--- | :--- | :--- | :--- |
| **Module A (Transaction + Call)** | `data/raw/module_a_transactions.csv` | **Hybrid ? real financial rows + synthetic telemetry** | IEEE-CIS, 590,540 rows; chronological holdout F1 0.1562, recall gain +11.39 pp under hypothetical telemetry priors. See [datasheet](DATASHEET.md). |
| **Module B (URL Checker)** | `data/raw/module_b_urls.csv` | **Active — trained on real historical URLs (2026-09-25)** | Kaggle Web page Phishing Detection v2: 11,427 unique URL texts after removing 3 duplicates. TF-IDF character n-grams + Logistic Regression; existing 50/50 rules blend retained. See provenance and limits below. |
| **Module C (Message / Screenshot)** | `data/raw/signature_examples.csv` | **Active ML + keyword safeguards; fear unvalidated** | 7,696 real-text examples; only 5 cited fear excerpts, OOF fear recall 0/5. Weak greed labels. See [Module C datasheet](MODULE_C_DATASHEET.md). |
| **Module D (Unified scorer)** | `data/raw/module_d_scenarios.csv` | **Learned logistic policy** | 2,000 synthetic joint scenarios using actual A/B/C outputs; OR source-label policy, not real incident labels. [Datasheet](MODULE_D_DATASHEET.md). |

---

## Module C: real text with weak behavioral labels

Sources: UCI SMS Spam Collection (CC BY 4.0), Kaggle Fraudulent E-mail Corpus v1
(CC BY-SA 4.0), and five short cited incident excerpts. The 7,696 examples contain
4,501 ham, 3,190 weak-labeled greed/opportunity and only 5 fear/authority examples.
No invented text pads the dataset. **Fear recall is 0/5 out of fold**; high greed/ham
metrics can exploit source/style and weak-label artifacts. See the
[Module C datasheet](MODULE_C_DATASHEET.md) for source links, exact labeling decisions,
per-class metrics, reproduction and license distinctions. Existing keyword safeguards
remain; classifier availability is not evidence of reliable fear recognition.

---

## Prerequisite Files for Training Phase

Training will only begin once all required dataset files are present in `data/raw/`:
- [x] `data/raw/module_a_transactions.csv` (Hybrid: real financial observations + synthetic telemetry)
- [x] `data/raw/module_b_urls.csv` (Real historical URLs; regenerate with the commands below)
- [x] `data/raw/module_c_sms.zip` (verified UCI source; pre-existing SMS CSV is not used)
- [x] `data/raw/signature_examples.csv` (real text + documented weak/manual signature labels)

## Module B: verified source and reproduction (2026-09-25)

The [Kaggle dataset](https://www.kaggle.com/datasets/shashwatwork/web-page-phishing-detection-dataset)
is public and downloadable without authentication, version 2, last updated June 27, 2021,
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Credit: Abdelhakim Hannousse and Salima Yahiouche, *Web page phishing detection*,
[Mendeley Data V3, DOI 10.17632/c2gw7fy2j4.3](https://data.mendeley.com/datasets/c2gw7fy2j4/3);
Kaggle mirror published by Shashwat Tiwari. Collection date: **May 2020**.

This is **not a mirror of UCI Phishing Websites (327)**. The
[UCI dataset](https://archive.ics.uci.edu/dataset/327/phishing+websites) is public, CC BY 4.0,
with 11,055 rows of numeric features, unsuitable for raw-URL character TF-IDF.
The downloaded Kaggle CSV has 11,430 rows, raw `url`, 87 extracted features, and `status`.
Only `url` and `status` are retained, with `status` renamed `label`. There is no evidence
from this check of either dataset having gone private; these are distinct formats/datasets.

```powershell
python ml/generate_module_b_data.py
python ml/train_module_b.py
python -m pytest tests/test_module_b.py tests/test_module_b_classifier.py -q
```

Offline ingestion of the verified download:
`python ml/generate_module_b_data.py --source data/raw/module_b_source_kaggle_v2.zip`.
An upstream CSV with `url,status` or canonical `url,label` is also accepted; local files
require independently verified provenance. Unknown labels, missing URLs and conflicting
labels are rejected. URL whitespace is stripped and lowercase text duplicates removed
because the existing vectorizer lowercases its input. No URLs are visited during ingestion,
training or tests. The old local 2,184-row CSV had unverified provenance; it was backed up
as `module_b_urls.csv.before-<hash>.bak` and **none of its rows were mixed into training**.

Verified source ZIP SHA-256:
`0bf65a186d58f312c2ed74c686eae418e6debb8b916f27079dbc718f3f1d1c02`.
Generated CSV SHA-256:
`588f85c75146706a255e8001738b75323443cd062a3c19896df24a999428374f`.
Generated metadata lives beside the CSV; metrics are saved to `ml/models/module_b.metrics.json`.
Raw data and the `.pkl` model remain gitignored; a fresh checkout needs the above commands.
Restart an already-running backend after retraining to clear its in-memory model cache.

**No Module B production-training rows or features are synthetic.** The final dataset contains
5,715 legitimate and 5,712 phishing URLs. TF-IDF features are computed from real URL strings;
the source's 87 numeric features are not used. Synthetic `.example` URLs appear only in
isolated unit tests, never in this dataset, saved production model, or reported evaluation.

The seed-42 stratified 80/20 split trains on 9,141 rows and tests on 2,286 (1,143 per class).
Phishing-positive precision **0.9173**, recall **0.9029**, F1 **0.9101**, FPR **0.0814**;
confusion counts: TN=1050, FP=93, FN=111, TP=1032. These are **classifier-only** results
at the default 0.5 decision threshold, not measurements of the blended score. They are not
suspiciously perfect, but 452 hostnames span both splits (805 test rows share a training
hostname). Related campaigns and near-duplicate paths can inflate random-split results.
This is an old balanced benchmark, not a contemporary deployment distribution or a
domain-disjoint/time-based evaluation. Modern short links, IDNs and Indian banking/UPI
campaign coverage have not been established; per-category recall is unmeasured.

**PhishTank supplement omitted.** Its [developer page](https://www.phishtank.org/developer_info.php)
still documents hourly bulk CSV/JSON downloads, descriptive User-Agent requirements and
application keys for automated downloads. However, its [terms page](https://phishtank.org/terms.php)
now labels the old free-data terms **archived** and points to
[Cisco's current terms](https://www.cisco.com/c/en/us/about/legal/cloud-and-software/end_user_license_agreement.html).
Permission for this ML-training use under the current terms is unclear. No feed was downloaded
or blended in; current phishing coverage is therefore not claimed.

## Module D

See [Module D datasheet](MODULE_D_DATASHEET.md) for synthetic labeling policy,
component split, contamination caveats, held-out metrics and coefficient spread.
Do not present these metrics as real-world performance.
