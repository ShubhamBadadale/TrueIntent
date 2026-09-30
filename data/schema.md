# TrueIntent — Dataset Schemas

This document defines the official data schemas for all datasets used across the TrueIntent ML pipeline. All incoming datasets (real or synthetic) stored in `data/raw/` or `data/processed/` must conform to these column definitions and types.

---

## 1. Module A: Source-unit Amount Benchmark

**Current scope:** Amount-only IEEE-CIS research benchmark. Real INR transfer
assessment is disabled. See [correctness update](../docs/MODULE_A_CORRECTNESS.md).

| Column | Type | Meaning |
|---|---|---|
| TransactionID | Integer | Source row identifier, audit/split only |
| TransactionDT | Numeric | Relative source seconds, chronological split only |
| amount | Finite nonnegative float | Unchanged TransactionAmt, original source units |
| amount_unit | Literal ieee_cis_source | Required explicit unit assertion |
| label | fraud or legitimate | Source isFraud mapped to the historical card-fraud target |

Only amount enters the model. No clock-hour, odd-hour, device, call-state or
velocity features are generated or used. Old datasets/artifacts are incompatible.
Missing or INR units cannot be converted implicitly. API timestamp, device and
telemetry fields are legacy metadata; a device ID is optional unless binding a
call report. Responses are benchmark scores, not transfer-risk verdicts.

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
| **Module A** | Source-unit amount only | Uncalibrated benchmark score | `data/raw/module_a_transactions.csv` |
| **Module B** | URL structure & domain features | Phishing probability | `data/raw/module_b_urls.csv` |
| **Module C** | Text content & psychological tactic | Scam probability + type | `data/raw/signature_examples.csv` |

## Legacy Android call report (not a scoring feature)

Transaction requests accept optional `call_telemetry` containing `device_id` (matching
transaction), `is_active_call` (boolean), and timezone-aware `timestamp` (fresh within
120 seconds, maximum 30 seconds future). This overrides the manual call flag only
for that request; none of these fields enter the amount-only model. Legacy Android requests without\nexplicit source units are rejected; real transaction scoring is disabled.
See [Android companion](../docs/ANDROID_COMPANION.md).

## Module D synthetic scenarios

`data/raw/module_d_scenarios.csv`: `module_a_score,module_b_score,module_c_score`
plus binary `combined_label`, `split`, `scenario_id`, `presence_mask`, `label_basis`
and per-component source IDs/labels. Absent scores are zero and labels are -1.
Combined labels are a synthetic OR policy, not real observed incident outcomes.
See [datasheet](MODULE_D_DATASHEET.md).
