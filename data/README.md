# TrueIntent — Dataset Sourcing & Usage Documentation

This directory contains datasets used for training and evaluating the ML modules of the TrueIntent fraud intent verification system.

---

> [!WARNING]
> ## PROMINENT NOTE: Module A Dataset is SYNTHETIC
> 
> **Module A (`data/raw/module_a_transactions.csv`) uses a synthetic dataset.**
> 
> Because real-world telemetry correlating banking transactions with live telephony call states (`is_active_call`) is highly confidential proprietary data, Module A relies on a synthetic dataset generated specifically for prototype modeling and schema validation.
> 
> ### Assumptions Used to Generate Module A Synthetic Data:
> 1. **Legitimate Transactions (~65% of samples):**
>    - **Amount:** Random distribution between ₹100.00 and ₹12,000.00.
>    - **Active Call (`is_active_call`):** Low probability (~8%) of coincidental ongoing phone calls during a transfer.
>    - **Transaction Velocity:** Low frequency (1 to 3 transactions in the prior 1 hour window).
> 2. **Fraudulent / APP Fraud Transactions (~35% of samples):**
>    - **Amount:** Higher value transfers between ₹15,000.00 and ₹150,000.00.
>    - **Active Call (`is_active_call`):** High probability (~90%) based on Authorised Push Payment (APP) fraud patterns where scammers maintain active call pressure/coercion on the victim during transfer.
>    - **Transaction Velocity:** Elevated frequency (3 to 10 rapid transfers in the prior 1 hour window) representing coerced multi-stage transfers.

---

## Dataset Sourcing Overview across Modules

| Module | Dataset File Path | Status (as of 2026-09-12) | Sourcing & Methodological Notes |
| :--- | :--- | :--- | :--- |
| **Module A (Transaction + Call)** | `data/raw/module_a_transactions.csv` | **Present — Synthetic** | Generated with domain-informed heuristics (APP fraud call correlation & velocity spikes). |
| **Module B (URL Checker)** | `data/raw/module_b_urls.csv` | **Pending — rules-only fallback active** | Intended to be a real phishing/benign URL dataset (e.g. PhishTank) provided by the project owner; not yet placed. `ml/train_module_b.py` prints DATASET PENDING and `check_url()` reports `ml_status: "rules_only (dataset pending)"` until then. |
| **Module C (Message / Screenshot)** | `data/raw/sms_spam_collection.csv`<br>`data/raw/signature_examples.csv` | **Pending — keyword-baseline fallback active** | Intended hybrid: base scam/legitimate labels from the real public **SMS Spam Collection Dataset** (UCI/Kaggle) + manually curated behavioral-signature sub-labels (`fear_authority`, `greed_opportunity`). Neither file is present yet; `analyze_message()` runs on the documented keyword baseline and `ml/train_module_c.py` prints DATASET PENDING until they are. |

---

## Methodological Note for Module C (Scam Analyzer)

The Module C dataset uses a **hybrid structure** by design:
1. **Base Layer (`/data/raw/sms_spam_collection.csv`):** Real, public SMS Spam Collection dataset providing broad coverage for general scam/spam vs. legitimate ("spam" vs. "ham") classification.
2. **Behavioral Signature Layer (`/data/raw/signature_examples.csv`):** Manually curated set of 40–60 targeted examples annotated with specific manipulation tactics:
   - `fear_authority`: Digital arrest, fake police/CBI/law enforcement coercion ("stay on the call", "under investigation").
   - `greed_opportunity`: Fake stock trading, guaranteed high-return investment schemes.

> [!NOTE]
> The dual-layer design is a deliberate methodological choice to address the lack of existing public NLP datasets categorized by psychological manipulation tactics.

---

## Prerequisite Files for Training Phase

Training will only begin once all required dataset files are present in `data/raw/`:
- [x] `data/raw/module_a_transactions.csv` (Synthetic — Generated)
- [ ] `data/raw/module_b_urls.csv` (Awaiting user placement — Module B runs rules-only until then)
- [ ] `data/raw/sms_spam_collection.csv` (Awaiting user placement — Module C runs keyword-baseline until then)
- [ ] `data/raw/signature_examples.csv` (Awaiting user placement — see above)
