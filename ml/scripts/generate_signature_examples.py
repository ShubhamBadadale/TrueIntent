#!/usr/bin/env python3
"""Generate synthetic signature examples for Module C.

Creates ~250 rows (125 per class) with a clear "SYNTHETIC — NOT REAL EVIDENCE" marker
in the text, written to `data/raw/signature_examples.csv`.
The CSV has columns: `text,signature`.
"""
import csv
import random
import os

# Import keyword lists from the existing module for realistic phrasing
try:
    from ml.predict_module_c import FEAR_AUTHORITY_KEYWORDS, GREED_OPPORTUNITY_KEYWORDS
except ImportError:
    # Fallback if running from repo root without package handling
    from predict_module_c import FEAR_AUTHORITY_KEYWORDS, GREED_OPPORTUNITY_KEYWORDS

random.seed(42)

NUM_PER_CLASS = 125
OUTPUT_PATH = os.path.join("data", "raw", "signature_examples.csv")

def _make_sentence(keywords, class_name):
    # Simple template: combine a random keyword with filler words.
    kw = random.choice(keywords)
    filler = [
        "please", "immediately", "urgent", "action required", "do not ignore",
        "respond now", "verify your account", "contact support", "security team",
        "your account will be locked",
    ]
    random.shuffle(filler)
    sentence = f"{kw.capitalize()} {' '.join(filler[:3])}."
    # Prepend synthetic marker
    return f"SYNTHETIC — NOT REAL EVIDENCE: {sentence}", class_name

rows = []
for _ in range(NUM_PER_CLASS):
    rows.append(_make_sentence(FEAR_AUTHORITY_KEYWORDS, "fear_authority"))
for _ in range(NUM_PER_CLASS):
    rows.append(_make_sentence(GREED_OPPORTUNITY_KEYWORDS, "greed_opportunity"))

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "signature"])
    for text, sig in rows:
        writer.writerow([text, sig])

print(f"[generate_signature_examples] Generated {len(rows)} synthetic rows → {OUTPUT_PATH}")
