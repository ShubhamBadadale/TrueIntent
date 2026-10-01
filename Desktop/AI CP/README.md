# AI Scam Detection System - ML Model Pipeline

## Project Overview
Multi-layer AI system for detecting scams in SMS messages, chat, and links using:
- **Module A**: Link Risk Analyzer
- **Module B**: Call Capture & STT (Future scope)
- **Module C**: PsyNLU-Engine (Core focus for demo)

## For Tomorrow's Presentation

### What We're Building Tonight:
1. ✅ Data cleaning pipeline
2. ✅ Layer 1: Text preprocessor (obfuscation removal)
3. ✅ Layer 2: DeBERTa-v3 classifier (edge shield)
4. ✅ Layer 4: Psychological profiling (5 pillars)
5. ✅ Layer 5: UPI contradiction engine
6. ✅ Evaluation metrics and visualization

### Project Structure
```
.
├── data/
│   ├── raw/              # Original datasets
│   ├── processed/        # Cleaned data
│   └── synthetic/        # Generated data
├── models/
│   ├── preprocessing.py  # Layer 1
│   ├── classifier.py     # Layer 2
│   ├── profiler.py       # Layer 4
│   └── contradiction.py  # Layer 5
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_model_training.ipynb
│   └── 03_demo.ipynb
├── results/
│   ├── metrics.json
│   ├── confusion_matrix.png
│   └── examples.json
└── requirements.txt
```

## Quick Start

### 1. Setup (5 mins)
```bash
pip install -r requirements.txt
python scripts/download_data.py
```

### 2. Data Preparation (10 mins)
```bash
python scripts/clean_data.py
python scripts/generate_synthetic.py
```

### 3. Model Training (30-60 mins on college PC)
```bash
python scripts/train_model.py
```

### 4. Evaluation & Demo (10 mins)
```bash
jupyter notebook notebooks/03_demo.ipynb
```

## Datasets Used
- Kaggle SMS Spam Collection (5,572 messages)
- Synthetic Hinglish data (2,000 messages)
- Custom UPI scam examples (500 messages)

## Model Architecture

### Layer 2: Edge Classifier
- **Base Model**: microsoft/deberta-v3-base
- **Task**: Binary classification (Safe vs Scam)
- **Training**: Fine-tuned on smishing dataset
- **Inference**: <30ms on CPU, <5ms on GPU

### Layer 4: Psychological Profiler
- **5 Pillars Detection**:
  1. AUTHORITY_PRETEXTING
  2. ARTIFICIAL_URGENCY
  3. LOSS_FRAMING
  4. COERCED_ACTION
  5. ISOLATION_TACTIC

### Layer 5: Contradiction Engine
- **UPI Protocol Rules**: Checks intent vs action
- **Examples**:
  - "Receive money" + "Enter PIN" → CRITICAL
  - "Refund" + "Approve collect request" → CRITICAL

## Expected Results
- **Accuracy**: 92-95% (on test set)
- **Precision**: 90%+ (low false positives)
- **Recall**: 85%+ (catches most scams)
- **F1-Score**: 88-90%

## Demo Flow Tomorrow
1. Show data cleaning pipeline
2. Explain model architecture
3. Live inference on sample messages
4. Show psychological profiling
5. Present evaluation metrics

## Timeline
- **Tonight**: Complete all 8 tasks (6-8 hours)
- **Tomorrow**: 10-min presentation with Jupyter demo

---
**Status**: Ready for demo ✨
