# TrueIntent — Dataset Schemas

This document defines the official data schemas for all datasets used across the TrueIntent ML pipeline. All incoming datasets (real or synthetic) stored in `data/raw/` or `data/processed/` must conform to these column definitions and types.

---

## 1. Module A: Transaction + Call Correlation Dataset

**Purpose:** Evaluates financial transaction risk combined with concurrent device state (e.g., active call status).

Phase 2 training CSV schema (runtime inference still accepts the existing six-feature
contract and its timestamp/device_id convenience inputs):

| Column | Type | Origin / meaning |
| :--- | :--- | :--- |
| `TransactionID` | Integer | Source row ID; audit only, not a feature |
| `TransactionDT` | Numeric | Relative source seconds; chronological split/history only |
| `amount` | Float | Real TransactionAmt in source units |
| `hour_of_day` | Integer 0?23 | Relative time phase proxy |
| `is_odd_hour` | Integer 0/1 | Existing hour rule on that proxy |
| `is_new_device` | Integer 0/1 | Synthetic novelty scenario |
| `is_active_call` | Integer 0/1 | Synthetic call scenario |
| `transaction_velocity` | Nonnegative integer | Prior-hour count for anonymized card/address proxy |
| `label` | Enum | Real source isFraud mapped to fraud/legitimate |

No deployment timestamp or device ID is fabricated. Exact definitions and provenance
are in [DATASHEET.md](DATASHEET.md). Only the six named features enter XGBoost.

---

## 2. Module B: URL Safety Checker Dataset

**Purpose:** Evaluates URL strings for phishing, typosquatting, deceptive domain structures, or malicious destinations.

| Column Name | Data Type | Constraint / Format | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `url` | String | Valid URL format string | Target web address to evaluate | `https://secure-update-hdfc.temp-domain.com/login` |
| `label` | String / Enum | `phishing` or `legitimate` | Target classification label | `phishing` |

---

## 3. Module C: Message / Screenshot Scam Analyzer Dataset

The assembled training file is `data/raw/signature_examples.csv`:

| Column | Meaning |
| :--- | :--- |
| `text` | Real message body or cited report excerpt |
| `signature` | `fear_authority`, `greed_opportunity`, or `none` |
| `source_url` | Per-example source citation |
| `source_id` | Source row number or incident identifier |
| `source_kind` | SMS, email or reported-excerpt type |
| `label_basis` | Original-label mapping, weak-label rule or manual annotation |
| `group_id` | Normalized text hash for deduplication |

Only `text` enters TF-IDF. The trainer consumes the complete assembled CSV without
supplementing a second ham file. The three signature names and inference contract
are unchanged. See [Module C datasheet](MODULE_C_DATASHEET.md).

---

## Summary Matrix

| Module | Primary Target Signal | Primary Output | Input Schema File |
| :--- | :--- | :--- | :--- |
| **Module A** | Transaction + Active Call correlation | Fraud probability | `data/raw/module_a_transactions.csv` |
| **Module B** | URL structure & domain features | Phishing probability | `data/raw/module_b_urls.csv` |
| **Module C** | Text content & psychological tactic | Scam probability + type | `data/raw/signature_examples.csv` |

## Optional Android call report (API only)

Transaction requests accept optional `call_telemetry` containing `device_id` (matching
transaction), `is_active_call` (boolean), and timezone-aware `timestamp` (fresh within
120 seconds, maximum 30 seconds future). This overrides the manual call flag only
for that request; it does not change the six-feature Module A training schema.
See [Android companion](../docs/ANDROID_COMPANION.md).

## Module D synthetic scenarios

`data/raw/module_d_scenarios.csv`: `module_a_score,module_b_score,module_c_score`
plus binary `combined_label`, `split`, `scenario_id`, `presence_mask`, `label_basis`
and per-component source IDs/labels. Absent scores are zero and labels are -1.
Combined labels are a synthetic OR policy, not real observed incident outcomes.
See [datasheet](MODULE_D_DATASHEET.md).
