"""
Data Cleaning Pipeline
Handles raw datasets and prepares them for training
"""

import pandas as pd
import numpy as np
import re
import os
from pathlib import Path
from sklearn.model_selection import train_test_split

# Create directories
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("DATA CLEANING PIPELINE")
print("=" * 60)
print()

# Step 1: Load Kaggle SMS Spam Dataset
print("Step 1: Loading Kaggle SMS Spam Dataset...")
print("-" * 60)

# Check if file exists
if os.path.exists("data/raw/spam.csv"):
    try:
        # Try different encodings
        for encoding in ['latin-1', 'utf-8', 'cp1252']:
            try:
                df = pd.read_csv("data/raw/spam.csv", encoding=encoding)
                print(f"✅ Loaded successfully with {encoding} encoding")
                break
            except:
                continue
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        print("Creating sample dataset instead...")
        df = create_sample_dataset()
else:
    print("⚠️ spam.csv not found in data/raw/")
    print("Creating sample dataset for demo...")
    df = create_sample_dataset()

print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print()

def create_sample_dataset():
    """Create sample dataset if Kaggle data not available"""
    
    scam_messages = [
        "URGENT: Your bank account will be blocked. Verify KYC at bit.ly/kyc123 immediately.",
        "Congratulations! You won Rs 50000. Enter UPI PIN to claim prize now.",
        "Your Aadhaar is suspended. Call 9876543210 and provide OTP to reactivate.",
        "SBI Alert: Suspicious activity. Update details at fake-sbi.com or account blocked.",
        "You have parcel. Pay Rs 200 customs at short.link/parcel within 2 hours.",
        "Electricity will be disconnected. Pay Rs 5000 penalty immediately or face legal action.",
        "KYC verification pending. Account will be closed. Click here within 24 hours.",
        "Police summons issued. Pay fine Rs 10000 now or arrest warrant will be issued.",
        "Loan of Rs 5 lakh approved. Submit PAN, Aadhaar and bank details urgently.",
        "Refund of Rs 15000 pending from bank. Approve UPI collect request within 10 min.",
        "Your credit card is blocked due to suspicious transaction. Call 8765432109 now.",
        "Income tax refund of Rs 25000. Enter your account details at income-tax.tk",
        "Amazon prize winner! Get iPhone 14. Pay delivery charge Rs 500 to receive.",
        "Your WhatsApp will expire. Click link to renew subscription immediately.",
        "RBI Alert: Your account KYC expired. Update at rbi-kyc.xyz within today.",
        "Urgent: Gas cylinder booking failed. Pay Rs 1500 penalty to avoid disconnection.",
        "You are selected for Govt subsidy Rs 20000. Submit Aadhaar to claim.",
        "Bank of India: Your debit card is blocked. Enter CVV at secure-link.com",
        "HDFC refund Rs 8000 credited. Accept payment request to receive amount.",
        "Airtel lucky draw winner! Rs 10000 prize. Share OTP to verify account.",
    ]
    
    legitimate_messages = [
        "Your OTP for login is 123456. Valid for 5 minutes. Do not share.",
        "Your Amazon order #12345 has been shipped. Track at amazon.in",
        "Meeting scheduled for tomorrow 3 PM. Please join on time.",
        "Your electricity bill of Rs 1500 is due on 15th. Pay online.",
        "Reminder: Doctor appointment tomorrow at 10 AM at City Hospital.",
        "Your credit card payment of Rs 5000 has been received. Thank you.",
        "Happy Birthday! Wishing you a wonderful year ahead.",
        "Flight booking confirmed. PNR: ABC123. Check-in opens 24 hrs before departure.",
        "Your Netflix subscription will renew on 1st Jan. Rs 649 will be charged.",
        "Package delivered successfully. Thank you for shopping with Flipkart!",
        "Bank statement for December is now available. Download from our app.",
        "Your mutual fund SIP of Rs 2000 is due on 5th. Ensure sufficient balance.",
        "Congratulations on your graduation! Best wishes for future endeavors.",
        "Cab booking confirmed. Driver: Raj, Number: MH-01-1234.",
        "Your Google Drive storage is 80% full. Upgrade to get more space.",
        "Reminder: Project submission deadline is 20th December.",
        "Your FASTag recharge of Rs 500 is successful. Balance: Rs 800.",
        "Meeting minutes shared. Please review and provide feedback.",
        "Your insurance premium of Rs 15000 is due on 1st Jan.",
        "Train ticket booked. PNR: 1234567890. Journey: 25th Dec.",
    ]
    
    data = []
    for msg in scam_messages:
        data.append({"text": msg, "label": "spam"})
    for msg in legitimate_messages:
        data.append({"text": msg, "label": "ham"})
    
    return pd.DataFrame(data)

# Step 2: Standardize column names
print("Step 2: Standardizing columns...")
print("-" * 60)

# Common patterns in SMS spam datasets
if 'v1' in df.columns and 'v2' in df.columns:
    df = df.rename(columns={'v1': 'label', 'v2': 'text'})
elif 'label' in df.columns and 'message' in df.columns:
    df = df.rename(columns={'message': 'text'})
elif 'Category' in df.columns and 'Message' in df.columns:
    df = df.rename(columns={'Category': 'label', 'Message': 'text'})

# Keep only required columns
if 'label' in df.columns and 'text' in df.columns:
    df = df[['label', 'text']]
else:
    print("❌ Required columns not found!")
    print(f"Available columns: {df.columns.tolist()}")
    exit(1)

print(f"✅ Columns standardized: {df.columns.tolist()}")
print()

# Step 3: Clean data
print("Step 3: Cleaning data...")
print("-" * 60)

initial_count = len(df)
print(f"Initial records: {initial_count}")

# Remove duplicates
df = df.drop_duplicates(subset=['text'])
print(f"After removing duplicates: {len(df)} (removed {initial_count - len(df)})")

# Remove null values
df = df.dropna()
print(f"After removing nulls: {len(df)}")

# Standardize labels
df['label'] = df['label'].str.lower().str.strip()
df['label'] = df['label'].map({'spam': 'scam', 'ham': 'legitimate', 'scam': 'scam', 'legitimate': 'legitimate'})

# Remove records with unknown labels
df = df[df['label'].isin(['scam', 'legitimate'])]

print(f"Final count: {len(df)}")
print(f"Label distribution:")
print(df['label'].value_counts())
print()

# Step 4: Text preprocessing
print("Step 4: Text preprocessing...")
print("-" * 60)

def clean_text(text):
    """Basic text cleaning"""
    if not isinstance(text, str):
        return ""
    
    # Convert to string and strip
    text = str(text).strip()
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove very short messages (likely corrupted)
    if len(text) < 10:
        return ""
    
    return text

df['text'] = df['text'].apply(clean_text)
df = df[df['text'] != ""]

print(f"✅ Text cleaned. Final count: {len(df)}")
print()

# Step 5: Add metadata
print("Step 5: Adding metadata...")
print("-" * 60)

df['length'] = df['text'].str.len()
df['word_count'] = df['text'].str.split().str.len()

# Detect potential scam keywords (for analysis)
scam_keywords = [
    'urgent', 'immediately', 'click', 'verify', 'account', 'block', 
    'suspend', 'expire', 'pin', 'otp', 'bank', 'kyc', 'prize', 'won',
    'congratulations', 'refund', 'claim', 'call now'
]

def count_keywords(text):
    text_lower = text.lower()
    return sum(1 for keyword in scam_keywords if keyword in text_lower)

df['scam_keyword_count'] = df['text'].apply(count_keywords)

print("✅ Metadata added:")
print(f"   - Text length")
print(f"   - Word count") 
print(f"   - Scam keyword count")
print()

# Step 6: Train/Val/Test Split
print("Step 6: Creating train/val/test splits...")
print("-" * 60)

# First split: 80% train+val, 20% test
train_val, test = train_test_split(
    df, 
    test_size=0.2, 
    random_state=42, 
    stratify=df['label']
)

# Second split: 75% train, 25% val (from train+val)
train, val = train_test_split(
    train_val, 
    test_size=0.25, 
    random_state=42, 
    stratify=train_val['label']
)

print(f"Train: {len(train)} samples ({len(train)/len(df)*100:.1f}%)")
print(f"Val:   {len(val)} samples ({len(val)/len(df)*100:.1f}%)")
print(f"Test:  {len(test)} samples ({len(test)/len(df)*100:.1f}%)")
print()

print("Label distribution:")
print("Train:", train['label'].value_counts().to_dict())
print("Val:  ", val['label'].value_counts().to_dict())
print("Test: ", test['label'].value_counts().to_dict())
print()

# Step 7: Save processed data
print("Step 7: Saving processed data...")
print("-" * 60)

train.to_csv("data/processed/train.csv", index=False)
val.to_csv("data/processed/val.csv", index=False)
test.to_csv("data/processed/test.csv", index=False)

# Save full dataset
df.to_csv("data/processed/full_cleaned.csv", index=False)

print("✅ Saved:")
print("   - data/processed/train.csv")
print("   - data/processed/val.csv")
print("   - data/processed/test.csv")
print("   - data/processed/full_cleaned.csv")
print()

# Step 8: Generate statistics
print("Step 8: Dataset Statistics")
print("-" * 60)

stats = {
    "total_samples": len(df),
    "scam_samples": len(df[df['label'] == 'scam']),
    "legitimate_samples": len(df[df['label'] == 'legitimate']),
    "avg_length": df['length'].mean(),
    "avg_word_count": df['word_count'].mean(),
    "avg_scam_keywords": df['scam_keyword_count'].mean(),
}

print(f"Total samples: {stats['total_samples']}")
print(f"Scam: {stats['scam_samples']} ({stats['scam_samples']/stats['total_samples']*100:.1f}%)")
print(f"Legitimate: {stats['legitimate_samples']} ({stats['legitimate_samples']/stats['total_samples']*100:.1f}%)")
print(f"Avg length: {stats['avg_length']:.1f} characters")
print(f"Avg words: {stats['avg_word_count']:.1f}")
print(f"Avg scam keywords: {stats['avg_scam_keywords']:.2f}")
print()

# Step 9: Sample preview
print("Step 9: Sample Preview")
print("-" * 60)
print("\n📧 Sample SCAM messages:")
for i, row in train[train['label'] == 'scam'].head(3).iterrows():
    print(f"\n{row['text'][:100]}...")

print("\n\n📧 Sample LEGITIMATE messages:")
for i, row in train[train['label'] == 'legitimate'].head(3).iterrows():
    print(f"\n{row['text'][:100]}...")

print()
print("=" * 60)
print("✅ DATA CLEANING COMPLETE!")
print("=" * 60)
print("\n🎯 Next step: Run python scripts/generate_synthetic.py")
print("   or directly: python scripts/train_model.py")
