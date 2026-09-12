# TrueIntent System Architecture

## Overview Architecture

```text
                        ┌─────────────────────────┐
                        │      Frontend (UI)       │
                        │  React — 3 input forms   │
                        └────────────┬─────────────┘
                                     │ REST calls
                        ┌────────────▼─────────────┐
                        │     API Layer (FastAPI)   │
                        └──┬───────┬───────┬────────┘
                                   │       │       │
              ┌────────────▼┐ ┌────▼────┐ ┌▼─────────────┐
              │ Module B     │ │ Module C │ │ Module A     │
              │ URL Checker  │ │ Msg/OCR  │ │ Txn+Call     │
              │ (rules + ML) │ │ Analyzer │ │ Correlation  │
              │              │ │ (OCR+NLP)│ │ (XGBoost)    │
              └────────────┬─┘ └────┬─────┘ └┬─────────────┘
                           │        │         │
                           └───┬────┴────┬────┘
                                ▼         ▼
                        ┌──────────────────────┐
                        │   Module D — Unified   │
                        │   Risk Scorer + SHAP   │
                        │   Explanation Engine   │
                        └───────────┬────────────┘
                                    ▼
                        ┌──────────────────────┐
                        │  Response: score +    │
                        │  plain-language why   │
                        └──────────────────────┘
```

## System Modules

### Module A: Transaction-Call Correlation Engine
- **Input**: Transaction amount, time, device signals, `is_active_call` flag, transaction velocity.
- **Model**: XGBoost tabular classifier.
- **Output**: Risk probability & feature contribution vector.

### Module B: Link/URL Safety Checker
- **Input**: User-provided URL.
- **Checks**: Domain age, structure, IP usage, typosquatting against known targets, redirect chain, security headers.
- **Output**: Safety risk score + diagnostic tags.

### Module C: Message/Screenshot Scam Analyzer
- **Input**: Raw text or image upload (processed via Tesseract OCR).
- **Checks**: Scans for Fear/Authority signature ("Digital Arrest") and Greed/Opportunity signature (fake investment returns). Automatically extracts and passes contained URLs to Module B.
- **Output**: Scam probability score + matched signature details.

### Module D: Unified Risk Scoring & SHAP Explanation Layer
- **Input**: Scores & feature vectors from Modules A, B, and C.
- **Logic**: Weighted ensemble scoring into risk tiers (**Low**, **Medium**, **High**, **Critical**).
- **Explainability**: Computes SHAP values and converts them to plain-language natural explanation sentences.

### Module E: Simple Web Portal (UI)
- **Framework**: React + Tailwind CSS.
- **Input Interfaces**: Check Link, Check Message/Screenshot, Simulate Transaction Scenario.
- **Results View**: Unified Risk Badge + Plain-Language Explanation Breakdown.
