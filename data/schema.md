# TrueIntent — Dataset Schemas

This document defines the official data schemas for all datasets used across the TrueIntent ML pipeline. All incoming datasets (real or synthetic) stored in `data/raw/` or `data/processed/` must conform to these column definitions and types.

---

## 1. Module A: Transaction + Call Correlation Dataset

**Purpose:** Evaluates financial transaction risk combined with concurrent device state (e.g., active call status).

| Column Name | Data Type | Constraint / Format | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `amount` | Float | Numeric (> 0.0) | Transaction value in currency units | `45000.00` |
| `timestamp` | String | ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) | Timestamp when the transaction was requested | `2026-09-12T20:54:00Z` |
| `device_id` | String | Non-empty alphanumeric string | Unique hardware/installation identifier | `dev_982a4f` |
| `is_active_call` | Boolean | `true` / `false` (or `1` / `0`) | Indicates if an active phone call was ongoing during transaction | `true` |
| `transaction_velocity` | Integer | Non-negative integer (>= 0) | Number of transactions initiated from device in the last 1 hour | `4` |
| `label` | String / Enum | `fraud` or `legitimate` | Target classification label | `fraud` |

---

## 2. Module B: URL Safety Checker Dataset

**Purpose:** Evaluates URL strings for phishing, typosquatting, deceptive domain structures, or malicious destinations.

| Column Name | Data Type | Constraint / Format | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `url` | String | Valid URL format string | Target web address to evaluate | `https://secure-update-hdfc.temp-domain.com/login` |
| `label` | String / Enum | `phishing` or `legitimate` | Target classification label | `phishing` |

---

## 3. Module C: Message / Screenshot Scam Analyzer Dataset

**Purpose:** Evaluates raw text (pasted chat text or extracted via OCR from screenshots) for scam behavioral signatures.

| Column Name | Data Type | Constraint / Format | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `raw_text` | String | Non-empty text string | Full message body or OCR output from chat screenshots | `"Urgent: CBI investigation registered against your Aadhar. Stay on call or face arrest."` |
| `label` | String / Enum | `scam` or `legitimate` | Binary scam classification label | `scam` |
| `scam_type` | String / Enum | `fear_authority`, `greed_opportunity`, or `none` | Psychological manipulation taxonomy matched | `fear_authority` |

> **Implementation note:** `ml/train_module_c.py` accepts common column-name variants for these
> fields (e.g. the UCI SMS Spam Collection's `v1`/`v2` layout, or `message`/`label`), mapping them
> onto this canonical schema. Curated signature rows live in `data/raw/signature_examples.csv`;
> ham rows from `data/raw/sms_spam_collection.csv` supplement the `none` class.

---

## Summary Matrix

| Module | Primary Target Signal | Primary Output | Input Schema File |
| :--- | :--- | :--- | :--- |
| **Module A** | Transaction + Active Call correlation | Fraud probability | `data/raw/module_a_transactions.csv` |
| **Module B** | URL structure & domain features | Phishing probability | `data/raw/module_b_urls.csv` |
| **Module C** | Text content & psychological tactic | Scam probability + type | `data/raw/signature_examples.csv` (+ `data/raw/sms_spam_collection.csv` ham supplement) |
