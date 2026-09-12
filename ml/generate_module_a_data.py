import random
import os
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_data(num_samples: int = 300, output_path: str = "data/raw/module_a_transactions.csv"):
    """
    Generates synthetic transaction + call state dataset for Module A.
    Adheres strictly to data/schema.md requirements.
    """
    random.seed(42)
    data = []
    start_time = datetime(2026, 9, 1, 0, 0, 0)

    # Device pools: established vs rare/new devices
    established_devices = [f"dev_{i:04d}" for i in range(1, 20)]
    new_devices = [f"dev_new_{i:04d}" for i in range(1, 50)]

    for i in range(num_samples):
        is_fraud = random.random() < 0.35  # ~35% fraud baseline
        
        # Fraud Skew: time of day, active call, velocity, device novelty
        if is_fraud:
            # Timestamp: skewed towards odd/night hours (23:00 to 05:00) or high-pressure windows
            is_odd = random.random() < 0.55
            if is_odd:
                hour = random.choice([23, 0, 1, 2, 3, 4, 5])
            else:
                hour = random.randint(6, 22)
            
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            day_offset = random.randint(0, 10)
            tx_datetime = start_time + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
            timestamp_str = tx_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Features
            amount = round(random.uniform(15000.0, 150000.0), 2)
            is_active_call = random.random() < 0.90  # 90% call correlation in APP fraud
            transaction_velocity = random.randint(3, 10)
            device_id = random.choice(new_devices if random.random() < 0.70 else established_devices)
            label = "fraud"

        else:
            # Legitimate: normal daytime hours, rare active call, low velocity, established devices
            hour = random.randint(7, 21)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            day_offset = random.randint(0, 10)
            tx_datetime = start_time + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
            timestamp_str = tx_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

            amount = round(random.uniform(100.0, 12000.0), 2)
            is_active_call = random.random() < 0.08  # 8% coincidental call
            transaction_velocity = random.randint(1, 3)
            device_id = random.choice(established_devices if random.random() < 0.85 else new_devices)
            label = "legitimate"

        data.append({
            "amount": amount,
            "timestamp": timestamp_str,
            "device_id": device_id,
            "is_active_call": is_active_call,
            "transaction_velocity": transaction_velocity,
            "label": label
        })

    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[Module A] Synthetic dataset successfully generated ({len(df)} samples) -> {output_path}")

if __name__ == "__main__":
    generate_synthetic_data()
