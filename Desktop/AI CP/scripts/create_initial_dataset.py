"""
Simple Dataset Creator - No Dependencies Required
Creates CSV dataset directly
"""

import csv
import random
import os

# Create directory
os.makedirs("data/raw", exist_ok=True)

print("=" * 70)
print(" " * 15 + "CREATING INITIAL DATASET")
print("=" * 70)
print()

# Scam message templates
scam_templates = [
    "URGENT: Your SBI account will be blocked in 24 hours. Verify KYC at bit.ly/verify or face legal action.",
    "Congratulations! You won Rs 50000 in PhonePe lottery. Enter UPI PIN at tinyurl.com/prize to claim.",
    "Your HDFC Bank KYC expired. Update at short.link/kyc within 2 hours or account suspended.",
    "Police notice: Your number linked to fraud. Call 9876543210 immediately or arrest warrant issued.",
    "Income Tax: Pay Rs 25000 penalty at secure-pay.tk within today or face prosecution.",
    "RBI Alert: Account blocked due to suspicious activity. Verify at bit.ly/unblock now.",
    "You have refund of Rs 15000 from Flipkart. Approve UPI collect request to receive money.",
    "Your Aadhaar card is suspended. Call 8765432109 and provide OTP to reactivate immediately.",
    "Customs duty Rs 500 pending for your parcel. Pay at short.link/customs within 12 hours.",
    "Electricity will be disconnected. Pay Rs 5000 penalty at paybill.tk or legal action.",
    "Your voter ID is invalid. Update at election-verify.tk within 24 hours or deleted.",
    "Bank Alert: Enter your CVV and PIN at secure-hdfc.tk to unblock your debit card.",
    "You are selected for Rs 5 lakh loan. Pay Rs 2000 processing at instamoney.tk",
    "Work from home job! Earn Rs 50000 monthly. Register at jobverify.tk with Rs 1000 fee.",
    "WhatsApp expiring soon. Renew subscription at wa-renew.tk by entering OTP and password.",
    "Amazon Prize: iPhone 14 winner! Pay Rs 500 delivery at prize-amazon.tk to receive.",
    "Your PAN card shows tax evasion Rs 100000. Pay immediately or CBI investigation.",
    "Gas cylinder booking failed. Pay Rs 1500 penalty at gasbook.tk within today.",
    "Court summons for case #1234. Pay Rs 10000 fine or arrest within 48 hours.",
    "Your credit card blocked. Re-verify at card-verify.tk by entering full card details.",
    
    # Hinglish scams
    "Aapka bank account block ho jayega. Turant bit.ly/kyc pe update karo within 24 hours.",
    "Urgent: Aapke naam par police case hai. 9876543210 par call karo immediately.",
    "Congratulations! Aapne Rs 50000 jeeta. Claim karo at prize.tk within 2 hours.",
    "Aapka Aadhaar suspended hai. Verify karo at aadhaar.tk immediately ya permanently block.",
    "Bank alert: Aapke account mein fraud activity. PIN share karo to verify account.",
    "Electricity bill Rs 5000 pending. Pay karo at bill.tk within today ya connection cut.",
    "Aap lucky draw winner hain! Rs 25000 prize. Details submit karo at winner.tk",
    "Income tax refund Rs 15000 approved. Claim karo by entering bank details at refund.tk",
    "Your UPI PIN expired. Update immediately at upi-update.tk to continue transactions.",
    "Gas connection band hoga. Rs 2000 deposit karo at gaspay.tk within 12 hours.",
]

# Legitimate message templates
legitimate_templates = [
    "Your OTP for Amazon login is 123456. Valid for 5 minutes. Do not share with anyone.",
    "Your Flipkart order #12345 has been shipped. Expected delivery: Tomorrow. Track at flipkart.com",
    "Meeting scheduled for 3 PM today. Join via Zoom link sent on email. Please be on time.",
    "Your electricity bill of Rs 1500 is due on 15th. Pay online at official website.",
    "Appointment reminder: Dr Sharma consultation tomorrow at 10 AM. City Hospital.",
    "Transaction successful. Rs 500 debited from SBI account. Balance: Rs 10000. Ref: ABC123.",
    "Your Netflix subscription will renew on 1st Jan. Amount: Rs 649. Manage at netflix.com",
    "Thank you for payment of Rs 2000. Receipt #9876. Transaction successful.",
    "Flight booking confirmed. PNR: XYZ123. Flight 6E-234. Departure: 25th Dec 10 AM.",
    "Your mutual fund SIP of Rs 5000 is due on 5th. Ensure sufficient bank balance.",
    "Bank statement for December available. Download from official SBI app.",
    "Package delivered successfully at your address. Order #56789. Thank you!",
    "Medicine reminder: Take capsule at 8 PM. Next dose in 8 hours. Health app.",
    "Class starts in 30 minutes. Topic: Machine Learning. Join Google Meet link.",
    "Happy Birthday! Wishing you joy and success. From all of us at company.",
    "Your FASTag recharge successful. Amount: Rs 500. Balance: Rs 1200. Valid till March.",
    "Cab arriving in 5 minutes. Driver: Raj. Car: MH-01-1234. Track on app.",
    "Delivery person at your gate. Order #11223. Please collect parcel. Swiggy.",
    "Your train ticket booked. PNR: 1234567890. Train: Rajdhani. Date: 20th Dec.",
    "Insurance premium Rs 15000 paid successfully. Policy active. Next due: 1st Jan.",
    "Loan EMI of Rs 10000 debited. Outstanding: Rs 500000. Next due: 1st Feb.",
    "Your credit card bill is Rs 25000. Due date: 20th. Pay to avoid charges.",
    "Congratulations! Your job application shortlisted. Interview on 15th at office.",
    "Meeting minutes shared. Please review and provide feedback by tomorrow.",
    "Your passport application approved. Collect from PSK Delhi on 25th. Bring docs.",
    "Exam results declared. Check official website with roll number. All the best!",
    "Your registration successful for webinar. Date: 22nd Dec 6 PM. Link on email.",
    "Booking confirmed at Hotel Taj. Check-in: 24th Dec. Booking ID: HTL123.",
    "Your driving license renewed. Valid till 2030. Download from Parivahan website.",
    "Electricity restored. Thank you for payment. Bill updated. Check online.",
]

# Create dataset
data = []

print("Creating scam messages...")
for template in scam_templates:
    data.append([template, "scam"])

print("Creating legitimate messages...")
for template in legitimate_templates:
    data.append([template, "legitimate"])

# Add more variations
print("Adding variations...")
for _ in range(50):
    # Random scam variations
    data.append([random.choice(scam_templates), "scam"])
    # Random legitimate variations
    data.append([random.choice(legitimate_templates), "legitimate"])

# Shuffle
random.shuffle(data)

# Write to CSV
print("Writing to file...")
with open("data/raw/spam.csv", "w", newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["text", "label"])  # Header
    writer.writerows(data)

print()
print("=" * 70)
print("✅ DATASET CREATED SUCCESSFULLY!")
print("=" * 70)
print()
print(f"Total messages: {len(data)}")
print(f"Scam messages: {sum(1 for d in data if d[1] == 'scam')}")
print(f"Legitimate messages: {sum(1 for d in data if d[1] == 'legitimate')}")
print()
print("File created: data/raw/spam.csv")
print()
print("=" * 70)
print("🎯 READY FOR NEXT STEP!")
print("=" * 70)
print()
print("Next: python scripts/clean_data.py")
print()
