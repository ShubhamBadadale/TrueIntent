"""
Generate Synthetic Hinglish and UPI Scam Data
To augment the training dataset
"""

import pandas as pd
import random
from pathlib import Path

Path("data/synthetic").mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("SYNTHETIC DATA GENERATION")
print("=" * 60)
print()

# UPI-specific scam templates
upi_scam_templates = [
    "Dear customer, refund of Rs {amount} is pending from {bank}. Approve UPI collect request within {time} to receive.",
    "You have received Rs {amount} cashback from {app}. Enter your UPI PIN to claim within {time}.",
    "Congratulations! Rs {amount} prize money. Accept payment request on {app} now.",
    "{bank} alert: Rs {amount} refund credited. Verify by entering PIN on {app}.",
    "You won Rs {amount} in lucky draw. Share UPI PIN at {url} to claim prize immediately.",
    "Urgent: Failed transaction. Re-enter UPI PIN to receive Rs {amount} refund.",
    "Your {app} wallet has Rs {amount} bonus. Approve collect request to add to balance.",
    "Cashback of Rs {amount} available. Enter OTP and PIN to credit to your account.",
    "{bank} refund Rs {amount}. Complete verification by sharing UPI credentials.",
    "You are eligible for Rs {amount} subsidy. Submit UPI ID and PIN for instant transfer.",
]

# KYC scam templates  
kyc_scam_templates = [
    "Your {bank} KYC is {status}. Update immediately at {url} within {time} or account will be {threat}.",
    "{bank} Alert: KYC verification pending. Click {url} to update details or face {threat}.",
    "Dear customer, your {bank} KYC expired. Verify at {url} within {time} to avoid {threat}.",
    "URGENT: {bank} KYC incomplete. Complete now at {url} or account {threat} in {time}.",
    "Final Notice: {bank} account KYC pending. Update at {url} immediately to prevent {threat}.",
    "Your {bank} KYC documents are {status}. Resubmit at {url} within {time}.",
    "RBI mandate: {bank} KYC renewal required. Visit {url} before {time} or {threat}.",
    "{bank}: Your account is under review due to incomplete KYC. Update at {url} now.",
    "KYC Alert: {bank} account will be {threat}. Verify identity at {url} within {time}.",
    "Immediate action required: {bank} KYC {status}. Click {url} to prevent {threat}.",
]

# Authority impersonation templates
authority_scam_templates = [
    "Police notice: You have {threat}. Contact {phone} immediately or face arrest warrant.",
    "Income Tax Dept: Your PAN shows {threat}. Pay penalty Rs {amount} at {url} within {time}.",
    "Court summons issued in your name. Pay fine Rs {amount} or {threat} within {time}.",
    "Cyber Crime Cell: Your number linked to fraud. Call {phone} immediately to clear name.",
    "RBI Alert: Your bank account has {threat}. Verify at {url} to avoid legal action.",
    "Customs Dept: Your parcel is held. Pay Rs {amount} duty at {url} within {time}.",
    "Telecom Authority: Your SIM will be {threat}. Re-verify at {url} immediately.",
    "Election Commission: Your voter ID is {threat}. Update details at {url} now.",
    "Govt subsidy of Rs {amount} approved. Submit Aadhaar and bank details at {url}.",
    "Municipal Corporation: Pay pending fine Rs {amount} within {time} or {threat}.",
]

# Hinglish variations (code-mixed)
hinglish_scam_templates = [
    "Aapka {bank} account {threat}. Turant {url} par verify karo within {time}.",
    "Congratulations! Aapne Rs {amount} jeeta hai. {url} pe claim karo abhi.",
    "Urgent: Aapka KYC {status} hai. {time} mein update nahi kiya toh account {threat}.",
    "Dear customer, aapka UPI refund Rs {amount} pending hai. PIN enter karke claim karo.",
    "Bank alert: Aapke account mein suspicious activity. {url} pe details update karo urgently.",
    "Aap lucky winner hain! Rs {amount} prize. {phone} pe call karke verify karo.",
    "Electricity bill pending hai. Rs {amount} pay karo {time} mein ya connection {threat}.",
    "Aapka Aadhaar {status} hai. {url} par jaldi verify karo otherwise {threat}.",
    "Police case aapke naam par hai. Rs {amount} fine pay karo ya {threat}.",
    "Gas connection {threat}. Rs {amount} deposit karo {url} pe within {time}.",
]

# Legitimate message templates
legitimate_templates = [
    "Your OTP for {service} is {otp}. Valid for 5 minutes. Do not share with anyone.",
    "Your {service} order #{order_id} has been {status}. Track at {service}.in",
    "Reminder: {event} scheduled for tomorrow at {time}. Please be on time.",
    "Your {service} bill of Rs {amount} is due on {date}. Pay online to avoid late fee.",
    "Thank you for your payment of Rs {amount}. Receipt #  {order_id}.",
    "Your {service} subscription will renew on {date}. Rs {amount} will be auto-debited.",
    "Booking confirmed. Reference: {order_id}. Check details in {service} app.",
    "Your transaction of Rs {amount} is successful. Balance: Rs {balance}.",
    "Meeting reminder: {event} at {time} today. Join link shared on email.",
    "Your {service} account has been created successfully. Login to get started.",
]

# Fill options
banks = ["SBI", "HDFC", "ICICI", "Axis Bank", "PNB", "Bank of India", "Canara Bank"]
apps = ["PhonePe", "GPay", "Paytm", "Amazon Pay", "BHIM"]
statuses = ["expired", "suspended", "blocked", "pending", "incomplete", "invalid", "under review"]
urls = ["bit.ly/verify", "tinyurl.com/kyc", "short.link/update", "secure-link.tk", "verify.xyz"]
times = ["24 hours", "2 hours", "30 minutes", "today", "immediately", "1 hour"]
threats = ["blocked", "suspended", "closed", "frozen", "terminated", "deactivated"]
amounts = ["500", "1000", "2000", "5000", "10000", "15000", "25000", "50000"]
phones = ["9876543210", "8765432109", "7654321098", "9999888877"]

services = ["Amazon", "Flipkart", "Swiggy", "Zomato", "Netflix", "Spotify"]
otps = ["123456", "987654", "456789", "321654"]
order_ids = ["ABC123", "XYZ789", "PQR456"]
statuses_legit = ["shipped", "delivered", "confirmed", "processed"]
events = ["Meeting", "Webinar", "Interview", "Appointment", "Class"]
times_legit = ["10 AM", "2 PM", "5 PM", "9 AM"]
dates = ["15th", "20th", "tomorrow", "next week", "1st Jan"]
balances = ["1000", "5000", "10000", "25000"]

def generate_message(templates, is_scam=True):
    """Generate one message from templates"""
    template = random.choice(templates)
    
    params = {
        "bank": random.choice(banks),
        "app": random.choice(apps),
        "status": random.choice(statuses),
        "url": random.choice(urls),
        "time": random.choice(times),
        "threat": random.choice(threats),
        "amount": random.choice(amounts),
        "phone": random.choice(phones),
        "service": random.choice(services),
        "otp": random.choice(otps),
        "order_id": random.choice(order_ids),
        "event": random.choice(events),
        "date": random.choice(dates),
        "balance": random.choice(balances),
    }
    
    try:
        message = template.format(**params)
        return message
    except:
        return template

# Generate datasets
def generate_dataset(n_samples=1000):
    """Generate synthetic dataset"""
    
    data = []
    
    # Distribution
    upi_scams = int(n_samples * 0.25)
    kyc_scams = int(n_samples * 0.15)
    authority_scams = int(n_samples * 0.10)
    hinglish_scams = int(n_samples * 0.10)
    legitimate = n_samples - (upi_scams + kyc_scams + authority_scams + hinglish_scams)
    
    print(f"Generating {n_samples} messages...")
    print(f"  - UPI scams: {upi_scams}")
    print(f"  - KYC scams: {kyc_scams}")
    print(f"  - Authority scams: {authority_scams}")
    print(f"  - Hinglish scams: {hinglish_scams}")
    print(f"  - Legitimate: {legitimate}")
    print()
    
    # Generate UPI scams
    for _ in range(upi_scams):
        data.append({
            "text": generate_message(upi_scam_templates),
            "label": "scam",
            "category": "upi_scam"
        })
    
    # Generate KYC scams
    for _ in range(kyc_scams):
        data.append({
            "text": generate_message(kyc_scam_templates),
            "label": "scam",
            "category": "kyc_scam"
        })
    
    # Generate authority scams
    for _ in range(authority_scams):
        data.append({
            "text": generate_message(authority_scam_templates),
            "label": "scam",
            "category": "authority_scam"
        })
    
    # Generate Hinglish scams
    for _ in range(hinglish_scams):
        data.append({
            "text": generate_message(hinglish_scam_templates),
            "label": "scam",
            "category": "hinglish_scam"
        })
    
    # Generate legitimate
    for _ in range(legitimate):
        data.append({
            "text": generate_message(legitimate_templates, is_scam=False),
            "label": "legitimate",
            "category": "legitimate"
        })
    
    # Shuffle
    random.shuffle(data)
    
    return pd.DataFrame(data)

# Generate train and test synthetic data
print("Generating training data (2000 samples)...")
train_synthetic = generate_dataset(2000)
train_synthetic.to_csv("data/synthetic/train_synthetic.csv", index=False)
print("✅ Saved: data/synthetic/train_synthetic.csv")
print()

print("Generating test data (500 samples)...")
test_synthetic = generate_dataset(500)
test_synthetic.to_csv("data/synthetic/test_synthetic.csv", index=False)
print("✅ Saved: data/synthetic/test_synthetic.csv")
print()

# Statistics
print("=" * 60)
print("STATISTICS")
print("=" * 60)
print(f"\nTraining Set ({len(train_synthetic)} samples):")
print(train_synthetic['label'].value_counts())
print("\nCategory breakdown:")
print(train_synthetic['category'].value_counts())

print(f"\nTest Set ({len(test_synthetic)} samples):")
print(test_synthetic['label'].value_counts())
print("\nCategory breakdown:")
print(test_synthetic['category'].value_counts())

print()
print("=" * 60)
print("✅ SYNTHETIC DATA GENERATION COMPLETE!")
print("=" * 60)
print("\n📊 Sample messages generated:")
print("\n🚨 UPI Scam:")
print(train_synthetic[train_synthetic['category'] == 'upi_scam'].iloc[0]['text'])
print("\n⚠️ Hinglish Scam:")
print(train_synthetic[train_synthetic['category'] == 'hinglish_scam'].iloc[0]['text'])
print("\n✅ Legitimate:")
print(train_synthetic[train_synthetic['category'] == 'legitimate'].iloc[0]['text'])
print()
print("🎯 Next step: python scripts/train_model.py")
