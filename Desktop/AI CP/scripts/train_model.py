"""
Complete Model Training Pipeline
Trains Layer 2 (DeBERTa classifier) + implements all other layers
"""

import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from pathlib import Path
from tqdm import tqdm

# Create directories
Path("models/saved").mkdir(parents=True, exist_ok=True)
Path("results").mkdir(parents=True, exist_ok=True)

print("=" * 70)
print(" " * 20 + "MODEL TRAINING PIPELINE")
print("=" * 70)
print()

# Check GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️  Device: {device}")
if device == "cuda":
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
print()

# ============================================================================
# STEP 1: LOAD DATA
# ============================================================================

print("STEP 1: Loading Data")
print("-" * 70)

# Load processed Kaggle data
train_kaggle = pd.read_csv("data/processed/train.csv")
val_kaggle = pd.read_csv("data/processed/val.csv")
test_kaggle = pd.read_csv("data/processed/test.csv")

print(f"✅ Kaggle data loaded:")
print(f"   Train: {len(train_kaggle)}")
print(f"   Val: {len(val_kaggle)}")
print(f"   Test: {len(test_kaggle)}")

# Load synthetic data if available
if os.path.exists("data/synthetic/train_synthetic.csv"):
    train_synthetic = pd.read_csv("data/synthetic/train_synthetic.csv")
    test_synthetic = pd.read_csv("data/synthetic/test_synthetic.csv")
    
    print(f"\n✅ Synthetic data loaded:")
    print(f"   Train: {len(train_synthetic)}")
    print(f"   Test: {len(test_synthetic)}")
    
    # Combine datasets
    train = pd.concat([train_kaggle, train_synthetic], ignore_index=True)
    test = pd.concat([test_kaggle, test_synthetic], ignore_index=True)
    
    print(f"\n📊 Combined dataset:")
    print(f"   Train: {len(train)}")
    print(f"   Val: {len(val_kaggle)}")
    print(f"   Test: {len(test)}")
else:
    print("\n⚠️  Synthetic data not found, using Kaggle data only")
    train = train_kaggle
    test = test_kaggle

val = val_kaggle

# Convert labels to numeric
label_map = {"legitimate": 0, "scam": 1}
train['label_id'] = train['label'].map(label_map)
val['label_id'] = val['label'].map(label_map)
test['label_id'] = test['label'].map(label_map)

print(f"\n📈 Label distribution (train):")
print(train['label'].value_counts())
print()

# ============================================================================
# STEP 2: CREATE DATASET CLASS
# ============================================================================

print("STEP 2: Creating PyTorch Datasets")
print("-" * 70)

class ScamDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# Load tokenizer
model_name = "microsoft/deberta-v3-base"
print(f"Loading tokenizer: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Create datasets
train_dataset = ScamDataset(
    train['text'].values,
    train['label_id'].values,
    tokenizer
)

val_dataset = ScamDataset(
    val['text'].values,
    val['label_id'].values,
    tokenizer
)

test_dataset = ScamDataset(
    test['text'].values,
    test['label_id'].values,
    tokenizer
)

print(f"✅ Datasets created:")
print(f"   Train: {len(train_dataset)} samples")
print(f"   Val: {len(val_dataset)} samples")
print(f"   Test: {len(test_dataset)} samples")
print()

# ============================================================================
# STEP 3: LOAD AND CONFIGURE MODEL
# ============================================================================

print("STEP 3: Loading Model")
print("-" * 70)

model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=2
)
model.to(device)

print(f"✅ Model loaded: {model_name}")
print(f"   Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
print()

# ============================================================================
# STEP 4: TRAINING CONFIGURATION
# ============================================================================

print("STEP 4: Configuring Training")
print("-" * 70)

training_args = TrainingArguments(
    output_dir="models/saved/checkpoints",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_steps=500,
    logging_dir="models/saved/logs",
    logging_steps=50,
    eval_strategy="steps",
    eval_steps=200,
    save_strategy="steps",
    save_steps=200,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    save_total_limit=2,
    report_to="none",
)

print("✅ Training configuration:")
print(f"   Epochs: {training_args.num_train_epochs}")
print(f"   Batch size: {training_args.per_device_train_batch_size}")
print(f"   Learning rate: {training_args.learning_rate}")
print()

# Metrics function
def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='binary'
    )
    acc = accuracy_score(labels, predictions)
    
    return {
        'accuracy': acc,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# ============================================================================
# STEP 5: TRAIN MODEL
# ============================================================================

print("STEP 5: Training Model")
print("-" * 70)
print("⏳ This may take 30-60 minutes on GPU, 2-3 hours on CPU...")
print()

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
)

# Train
trainer.train()

print("\n✅ Training completed!")
print()

# ============================================================================
# STEP 6: EVALUATE ON TEST SET
# ============================================================================

print("STEP 6: Evaluating on Test Set")
print("-" * 70)

test_results = trainer.evaluate(test_dataset)

print("📊 Test Results:")
print(f"   Accuracy:  {test_results['eval_accuracy']:.4f}")
print(f"   Precision: {test_results['eval_precision']:.4f}")
print(f"   Recall:    {test_results['eval_recall']:.4f}")
print(f"   F1 Score:  {test_results['eval_f1']:.4f}")
print()

# Get predictions
predictions = trainer.predict(test_dataset)
y_pred = np.argmax(predictions.predictions, axis=1)
y_true = test['label_id'].values

# Confusion matrix
cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=['Legitimate', 'Scam'],
            yticklabels=['Legitimate', 'Scam'])
plt.title('Confusion Matrix - Layer 2 Classifier', fontsize=14, fontweight='bold')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.savefig('results/confusion_matrix.png', dpi=300)
print("✅ Confusion matrix saved: results/confusion_matrix.png")
print()

# ============================================================================
# STEP 7: SAVE MODEL
# ============================================================================

print("STEP 7: Saving Model")
print("-" * 70)

model.save_pretrained("models/saved/layer2_classifier")
tokenizer.save_pretrained("models/saved/layer2_classifier")

print("✅ Model saved to: models/saved/layer2_classifier/")
print()

# Save metrics
metrics = {
    "test_accuracy": float(test_results['eval_accuracy']),
    "test_precision": float(test_results['eval_precision']),
    "test_recall": float(test_results['eval_recall']),
    "test_f1": float(test_results['eval_f1']),
    "confusion_matrix": cm.tolist(),
    "model_name": model_name,
    "training_samples": len(train),
    "test_samples": len(test)
}

with open("results/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("✅ Metrics saved to: results/metrics.json")
print()

# ============================================================================
# STEP 8: TEST INFERENCE
# ============================================================================

print("STEP 8: Testing Inference")
print("-" * 70)

def predict_message(text):
    """Quick inference function"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        pred = torch.argmax(probs, dim=1)
    
    return {
        "prediction": "scam" if pred.item() == 1 else "legitimate",
        "confidence": probs[0][pred].item(),
        "scam_probability": probs[0][1].item()
    }

# Test messages
test_messages = [
    "URGENT: Your bank account will be blocked. Verify KYC at bit.ly/kyc123",
    "Your OTP is 123456. Valid for 5 minutes. Do not share.",
    "Congratulations! You won Rs 50000. Enter UPI PIN to claim prize.",
    "Your Amazon order has been shipped. Track at amazon.in",
]

print("Testing sample messages:\n")
for msg in test_messages:
    result = predict_message(msg)
    print(f"Message: {msg[:60]}...")
    print(f"Prediction: {result['prediction'].upper()} (confidence: {result['confidence']:.3f})")
    print()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("=" * 70)
print("✅ MODEL TRAINING COMPLETE!")
print("=" * 70)
print()
print("📁 Files created:")
print("   - models/saved/layer2_classifier/")
print("   - results/metrics.json")
print("   - results/confusion_matrix.png")
print()
print("📊 Final Metrics:")
print(f"   Accuracy:  {test_results['eval_accuracy']*100:.2f}%")
print(f"   Precision: {test_results['eval_precision']*100:.2f}%")
print(f"   Recall:    {test_results['eval_recall']*100:.2f}%")
print(f"   F1 Score:  {test_results['eval_f1']*100:.2f}%")
print()
print("🎯 Next step: jupyter notebook notebooks/03_demo.ipynb")
print()
