# 📊 Datasets for AI Scam Detection

## Directory Structure

```
data/
├── raw/                    # Original/downloaded datasets
│   └── spam.csv           # Main training dataset (✅ CREATED)
├── processed/             # Cleaned and split datasets (created after cleaning)
│   ├── train.csv         # Training set (60%)
│   ├── val.csv           # Validation set (20%)
│   └── test.csv          # Test set (20%)
└── synthetic/             # Generated synthetic data (created after generation)
    ├── train_synthetic.csv
    └── test_synthetic.csv
```

---

## ✅ Current Status

### 1. Base Dataset (data/raw/spam.csv)
- **Status**: ✅ Created
- **Size**: 160 messages
- **Format**: CSV with columns: `text`, `label`
- **Labels**: 
  - `scam` - Scam/phishing messages
  - `legitimate` - Safe messages
- **Distribution**: 50% scam, 50% legitimate

### 2. Processed Datasets (data/processed/)
- **Status**: ⏳ Will be created when you run `python scripts/clean_data.py`
- **Contents**:
  - `train.csv` - 60% of data (96 samples)
  - `val.csv` - 20% of data (32 samples)
  - `test.csv` - 20% of data (32 samples)

### 3. Synthetic Datasets (data/synthetic/)
- **Status**: ⏳ Will be created when you run `python scripts/generate_synthetic.py`
- **Contents**:
  - `train_synthetic.csv` - 2,000 generated samples
  - `test_synthetic.csv` - 500 generated samples
- **Categories**:
  - UPI scams
  - KYC phishing
  - Authority impersonation
  - Prize/lottery scams
  - Hinglish scams
  - Legitimate messages

---

## 📁 Dataset Details

### Base Dataset (spam.csv)

**Scam Categories:**
1. **UPI Scams**: Fake refunds, collect requests, prize money
2. **KYC Phishing**: Bank account verification, expired KYC
3. **Authority Impersonation**: Police, income tax, court notices
4. **Prize/Lottery**: Fake winnings, lucky draw
5. **Job/Loan Scams**: Work from home, instant loans
6. **Hinglish Scams**: Code-mixed English-Hindi messages

**Legitimate Categories:**
1. OTP messages
2. Order confirmations
3. Appointment reminders
4. Bill payments
5. Transaction confirmations
6. Booking confirmations
7. General notifications

**Sample Scam:**
```
URGENT: Your SBI account will be blocked in 24 hours. 
Verify KYC at bit.ly/verify or face legal action.
```

**Sample Legitimate:**
```
Your OTP for Amazon login is 123456. Valid for 5 minutes. 
Do not share with anyone.
```

---

## 🔄 Data Pipeline

### Step 1: Create Base Dataset
```bash
python scripts/create_initial_dataset.py
```
**Output**: `data/raw/spam.csv` (✅ Done!)

### Step 2: Clean and Split Data
```bash
python scripts/clean_data.py
```
**What it does**:
- Removes duplicates
- Handles missing values
- Normalizes text
- Creates train/val/test splits

**Output**: 
- `data/processed/train.csv`
- `data/processed/val.csv`
- `data/processed/test.csv`

### Step 3: Generate Synthetic Data (Optional)
```bash
python scripts/generate_synthetic.py
```
**What it does**:
- Generates 2,500 additional training samples
- Creates variations of scam patterns
- Includes Hinglish code-mixed messages
- Focuses on Indian scam types

**Output**:
- `data/synthetic/train_synthetic.csv`
- `data/synthetic/test_synthetic.csv`

---

## 📈 Expected Final Dataset Size

After running all scripts:

| Dataset | Samples | Purpose |
|---------|---------|---------|
| Base (Kaggle) | 160 | Original data |
| Synthetic | 2,500 | Augmentation |
| **Total Training** | **~2,100** | Model training |
| **Validation** | **~500** | Hyperparameter tuning |
| **Test** | **~600** | Final evaluation |

---

## 🎯 Dataset Features

### Text Features:
- **Length**: 10-200 characters
- **Languages**: English, Hinglish (Romanized Hindi)
- **Content**: SMS-style messages
- **Obfuscation**: Some contain leetspeak, zero-width chars

### Label Distribution:
- **Balanced**: ~50% scam, ~50% legitimate
- **Representative**: Covers common Indian scam patterns
- **Diverse**: Multiple scam categories

---

## 🔍 Data Quality

### Scam Messages Include:
✅ Authority pretexting (bank, police)  
✅ Artificial urgency (time pressure)  
✅ Loss framing (account blocked)  
✅ Coerced action (enter PIN, click link)  
✅ UPI-specific patterns  
✅ Hinglish code-mixing  

### Legitimate Messages Include:
✅ Real OTP patterns  
✅ Actual order confirmations  
✅ Bill reminders  
✅ Appointment notifications  
✅ Transaction receipts  

---

## 💡 For Better Results (Optional)

### Option 1: Download Kaggle SMS Spam Dataset

**Larger dataset for better accuracy:**

1. Go to: https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset
2. Download `spam.csv`
3. Replace `data/raw/spam.csv` with downloaded file
4. Re-run cleaning: `python scripts/clean_data.py`

**Benefits:**
- 5,572 messages (vs 160)
- Better model accuracy
- More diverse patterns

### Option 2: Add Your Own Data

Create a CSV file with format:
```csv
text,label
"Your message here",scam
"Another message",legitimate
```

Add to `data/raw/` and include in cleaning script.

---

## 🚀 Quick Start

```bash
# Already done:
✅ python scripts/create_initial_dataset.py

# Next steps:
python scripts/clean_data.py
python scripts/generate_synthetic.py
python scripts/train_model.py
```

---

## 📊 Dataset Statistics

Run this to see statistics:
```python
import pandas as pd

# Load data
df = pd.read_csv('data/raw/spam.csv')

print(f"Total: {len(df)}")
print(f"Scam: {len(df[df['label']=='scam'])}")
print(f"Legitimate: {len(df[df['label']=='legitimate'])}")
print(f"Avg length: {df['text'].str.len().mean():.0f} chars")
```

---

## ✅ Checklist

- [x] Base dataset created (`spam.csv`)
- [ ] Data cleaned and split (run `clean_data.py`)
- [ ] Synthetic data generated (run `generate_synthetic.py`)
- [ ] Model trained (run `train_model.py`)

---

## 🎓 Dataset Citations

### Original Inspiration:
- **Kaggle SMS Spam Collection**: UCI Machine Learning Repository
- **COVA-X**: Multi-turn conversational phishing dataset
- **ASsET**: Authority scam and social engineering texts

### Our Contribution:
- Indian-specific scam patterns
- UPI fraud scenarios
- Hinglish code-mixed messages
- Psychological manipulation tactics

---

**Your dataset is ready! Proceed to data cleaning and training.** 🚀
