"""
Comprehensive Dataset Setup Script
Creates datasets directly without needing external downloads
"""

import pandas as pd
import os
from pathlib import Path
import random

# Create directories
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/synthetic").mkdir(parents=True, exist_ok=True)

print("=" * 70)
print(" " * 15 + "DATASET SETUP FOR AI SCAM DETECTION")
print("=" * 70)
print()

# ============================================================================
# COMPREHENSIVE SCAM MESSAGE DATABASE
# ============================================================================

# UPI Scams (100 variations)
upi_scams = [
    "URGENT: SBI Bank refund of Rs {} pending. Approve UPI collect request within {} to receive money.",
    "Congratulations! Cashback of Rs {} from PhonePe. Enter UPI PIN to claim your reward now.",
    "You have received Rs {} prize money from {} lucky draw. Accept payment request immediately.",
    "Dear customer, Rs {} refund credited to your account. Verify by entering PIN on GPay.",
    "Your {} wallet has bonus Rs {}. Approve collect request to add to your balance.",
    "Bank Alert: Failed transaction. Re-enter UPI PIN to receive Rs {} refund from HDFC.",
    "You won Rs {} in Amazon Pay quiz. Share UPI PIN to credit amount within {}.",
    "Urgent: Your {} account has Rs {} cashback pending. Enter OTP and PIN to claim.",
    "Congratulations! Rs {} lottery prize approved. Submit UPI credentials for instant transfer.",
    "Refund of Rs {} from {}. Complete verification by sharing UPI PIN and OTP.",
]

# KYC / Banking Scams (100 variations)
kyc_scams = [
    "Your {} KYC is expired. Account will be blocked in {}. Update immediately at {} or face legal action.",
    "{} Alert: KYC verification pending. Click {} to update details within {} or account suspended.",
    "URGENT: {} account KYC incomplete. Verify at {} within {} to prevent permanent closure.",
    "Final Notice: Your {} KYC documents are invalid. Resubmit at {} before {} expires.",
    "RBI mandate: {} KYC renewal required. Visit {} immediately or account will be frozen.",
    "Your {} debit card is blocked due to incomplete KYC. Update at {} within {}.",
    "{} account under review. Complete KYC verification at {} within {} to avoid suspension.",
    "Dear customer, {} KYC expired. Update documents at {} or account closed in {}.",
    "Security Alert: {} account KYC pending verification. Click {} now to prevent deactivation.",
    "Immediate action required: {} KYC invalid. Update at {} within {} or face penalty.",
]

# Authority Impersonation (100 variations)
authority_scams = [
    "Police Cyber Crime: Your phone linked to fraud case #{}. Call {} immediately or arrest warrant issued.",
    "Income Tax Department: PAN {} shows tax evasion of Rs {}. Pay penalty at {} within {}.",
    "Court Notice: Summons issued for case #{}. Pay fine Rs {} or legal action within {}.",
    "RBI Alert: Your bank account {} has suspicious activity. Verify at {} to avoid freezing.",
    "Customs Department: Your parcel {} is held. Pay duty Rs {} at {} within {}.",
    "Telecom Authority: Your SIM card {} will be blocked. Re-verify at {} immediately.",
    "Election Commission: Voter ID {} is suspended. Update details at {} within {}.",
    "CBI Investigation: Your account involved in fraud. Contact {} immediately to clear name.",
    "Municipal Corporation: Pending fine Rs {} for violation #{}. Pay at {} or legal action.",
    "GST Department: Return filing pending. Pay Rs {} penalty at {} within {} to avoid prosecution.",
]

# Prize/Lottery Scams (50 variations)
prize_scams = [
    "Congratulations! You won Rs {} in {} lucky draw. Claim at {} within {}.",
    "You are selected for {} gift voucher worth Rs {}. Click {} to claim prize.",
    "{} lottery winner! Prize: Rs {}. Share details at {} to receive amount.",
    "You won {} in contest! Verify at {} and pay processing fee Rs {} to claim.",
    "Congratulations! {} prize of Rs {} approved. Submit documents at {} immediately.",
]

# Fake Jobs/Loans (50 variations)
job_loan_scams = [
    "Congratulations! Selected for {} job with salary Rs {}. Pay registration Rs {} at {}.",
    "Loan of Rs {} lakh approved instantly. Submit fee Rs {} at {} for processing.",
    "Work from home opportunity. Earn Rs {} daily. Register at {} with fee Rs {}.",
    "Personal loan Rs {} sanctioned. Pay Rs {} processing at {} for immediate disbursal.",
    "Government job notification. Apply at {} with Rs {} registration before {}.",
]

# Hinglish Scams (100 variations)
hinglish_scams = [
    "Aapka {} account block ho jayega. Turant {} pe KYC update karo within {}.",
    "Urgent: Aapke naam par police case hai. {} par call karo immediately ya arrest hoga.",
    "Congratulations! Aapne Rs {} jeeta hai {} mein. {} pe claim karo abhi.",
    "Aapka {} KYC expired hai. {} mein update nahi kiya toh account band ho jayega.",
    "Bank alert: Aapke account mein suspicious activity. {} pe verify karo urgently.",
    "Aap lucky winner hain! Rs {} prize. {} pe details submit karo immediately.",
    "Electricity bill pending Rs {}. {} mein pay karo ya connection katega.",
    "Aapka Aadhaar suspended hai. {} pe verify karo within {} otherwise blocked.",
    "Gas cylinder booking failed. Rs {} penalty pay karo {} pe ya disconnection.",
    "Income tax refund Rs {} pending. {} pe claim karo within {} days.",
]

# LEGITIMATE MESSAGES (500 variations)
legitimate_messages = [
    "Your OTP for {} login is {}. Valid for 5 minutes. Do not share this with anyone.",
    "Your {} order #{} has been shipped. Expected delivery: {}. Track at {}.in",
    "Meeting reminder: {} scheduled for {} at {}. Please join on time.",
    "Your {} bill of Rs {} is due on {}. Pay online to avoid late charges.",
    "Appointment confirmed with Dr {} on {} at {}. Clinic: {}.",
    "Transaction successful. Rs {} debited from your {} account. Balance: Rs {}.",
    "Your {} subscription will renew on {}. Amount: Rs {}. Manage at {}.in",
    "Thank you for your payment of Rs {}. Receipt #{}. Transaction ID: {}.",
    "Booking confirmed. PNR: {}. Train: {}. Date: {}. Journey: {} to {}.",
    "Your flight booking is confirmed. PNR: {}. Flight: {}. Departure: {} at {}.",
    "Cab booking confirmed. Driver: {}. Car: {}. ETA: {} mins. Track in app.",
    "Your delivery has arrived. Order #{}. Please collect from reception.",
    "Medicine reminder: Take {} at {}. Next dose in {} hours.",
    "Class reminder: {} starts in 30 minutes. Join link: {}",
    "Your mutual fund SIP of Rs {} is due on {}. Ensure sufficient balance.",
    "Account statement for {} is ready. Download from {} app or website.",
    "Congratulations! Your loan has been disbursed. Amount: Rs {}. Check account.",
    "Your insurance policy #{} is active. Premium: Rs {}. Next due: {}.",
    "Birthday wishes! {} wishes you a wonderful year ahead. Celebrate!",
    "Your FASTag recharge successful. Amount: Rs {}. Balance: Rs {}.",
]

# Function to fill templates with random values
def fill_template(template):
    """Fill template with random realistic values"""
    banks = ["SBI", "HDFC", "ICICI", "Axis Bank", "PNB", "Bank of India", "Canara Bank", "IDBI"]
    companies = ["Amazon", "Flipkart", "Paytm", "PhonePe", "Google Pay", "BHIM", "Swiggy", "Zomato"]
    amounts = ["500", "1000", "2000", "5000", "8000", "10000", "15000", "25000", "50000", "1 lakh"]
    times = ["24 hours", "2 hours", "30 minutes", "today", "48 hours", "12 hours"]
    urls = ["bit.ly/verify", "tinyurl.com/kyc", "short.link/bank", "secure-verify.tk"]
    phones = ["9876543210", "8765432109", "7654321098", "9999888877", "8888777766"]
    
    # Try to format with available placeholders
    try:
        return template.format(
            random.choice(banks),
            random.choice(amounts),
            random.choice(times),
            random.choice(urls),
            random.choice(companies),
            random.choice(phones),
            random.randint(1000, 9999),
            random.choice(["Monday", "Tuesday", "tomorrow", "15th", "20th"]),
            random.choice(["India", "Mumbai", "Delhi", "Bangalore"]),
            random.choice(["123456", "987654", "ABC123", "XYZ789"])
        )
    except:
        return template

# Generate complete dataset
print("Generating comprehensive dataset...")
print("-" * 70)

all_data = []

# Generate UPI scams
print("Generating UPI scams...")
for template in upi_scams:
    for _ in range(10):  # 10 variations each
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "upi_scam"
        })

# Generate KYC scams
print("Generating KYC/Banking scams...")
for template in kyc_scams:
    for _ in range(10):
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "kyc_scam"
        })

# Generate Authority scams
print("Generating Authority impersonation scams...")
for template in authority_scams:
    for _ in range(10):
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "authority_scam"
        })

# Generate Prize scams
print("Generating Prize/Lottery scams...")
for template in prize_scams:
    for _ in range(10):
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "prize_scam"
        })

# Generate Job/Loan scams
print("Generating Job/Loan scams...")
for template in job_loan_scams:
    for _ in range(10):
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "job_loan_scam"
        })

# Generate Hinglish scams
print("Generating Hinglish scams...")
for template in hinglish_scams:
    for _ in range(10):
        all_data.append({
            "text": fill_template(template),
            "label": "scam",
            "category": "hinglish_scam"
        })

# Generate Legitimate messages
print("Generating Legitimate messages...")
for template in legitimate_messages:
    for _ in range(10):  # 10 variations each
        all_data.append({
            "text": fill_template(template),
            "label": "legitimate",
            "category": "legitimate"
        })

# Shuffle the data
random.shuffle(all_data)

# Create DataFrame
df = pd.DataFrame(all_data)

# Save as spam.csv (compatible with Kaggle format)
df_kaggle = df[['text', 'label']].copy()
df_kaggle.to_csv("data/raw/spam.csv", index=False)

print()
print("=" * 70)
print("✅ DATASET GENERATION COMPLETE!")
print("=" * 70)
print()
print(f"Total messages generated: {len(df):,}")
print()
print("Breakdown by category:")
print(df['category'].value_counts())
print()
print("Label distribution:")
print(df['label'].value_counts())
print()
print("Files created:")
print("  ✅ data/raw/spam.csv")
print()
print("=" * 70)
print("🎯 READY FOR TRAINING!")
print("=" * 70)
print()
print("Next steps:")
print("1. Run: python scripts/clean_data.py")
print("2. Run: python scripts/train_model.py")
print()
