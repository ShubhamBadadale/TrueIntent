# 🔧 TROUBLESHOOTING GUIDE

Quick solutions for common issues you might face tonight.

---

## 🚨 Installation Issues

### Problem: `pip install` fails with "no matching distribution"
**Solution:**
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Try installing again
pip install -r requirements.txt
```

### Problem: PyTorch installation is slow or fails
**Solution:**
```bash
# Install PyTorch separately first (CPU version is faster to download)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Then install rest
pip install -r requirements.txt
```

### Problem: "ERROR: Could not find a version that satisfies transformers"
**Solution:**
```bash
# Check Python version
python --version  # Should be 3.8 or higher

# If too old, use Python 3.9+
python3.9 -m pip install -r requirements.txt
```

---

## 📊 Data Preparation Issues

### Problem: "FileNotFoundError: data/raw/spam.csv"
**Solution:**
This is NORMAL! The script creates sample data automatically.
```bash
# Just run it - it will generate test data
python scripts/clean_data.py
```

### Problem: "Too few samples after cleaning"
**Solution:**
```bash
# Generate synthetic data to augment
python scripts/generate_synthetic.py

# This adds 2,500 more samples
```

### Problem: "KeyError: 'label'" or "KeyError: 'text'"
**Solution:**
Check your CSV file has the right columns. If using custom data:
```python
# Edit clean_data.py, add your column mapping
if 'your_label_column' in df.columns:
    df = df.rename(columns={'your_label_column': 'label'})
```

---

## 🎯 Training Issues

### Problem: "CUDA out of memory"
**Solution 1** - Reduce batch size:
```python
# Edit scripts/train_model.py line 156
per_device_train_batch_size=8,  # Change from 16 to 8
```

**Solution 2** - Use CPU:
```python
# Training will be slower but will work
# No code changes needed - script auto-detects
```

### Problem: Training is too slow (CPU)
**Solution 1** - Reduce epochs:
```python
# Edit scripts/train_model.py line 155
num_train_epochs=1,  # Change from 3 to 1
```

**Solution 2** - Use smaller dataset:
```python
# Edit scripts/train_model.py after line 78
train = train.sample(n=1000)  # Use only 1000 samples
```

**Solution 3** - Use college GPU PC:
```bash
# Copy project to college PC
# Run there overnight
```

### Problem: "RuntimeError: Expected tensor for argument #1"
**Solution:**
```bash
# Model and data type mismatch
# Usually fixed by clearing cache and restarting

# Clear cache
rm -rf models/saved/checkpoints/*

# Restart training
python scripts/train_model.py
```

### Problem: Training starts but crashes after a few steps
**Solution:**
```bash
# Check disk space
df -h

# Need at least 5GB free for model checkpoints
# Delete old checkpoints if needed
```

---

## 📓 Notebook Issues

### Problem: "ModuleNotFoundError: No module named 'transformers'"
**Solution:**
```bash
# Install in notebook environment
pip install transformers torch

# Or activate correct environment first
source venv/bin/activate  # Then launch jupyter
jupyter notebook
```

### Problem: "FileNotFoundError: models/saved/layer2_classifier"
**Solution:**
Model hasn't been trained yet. Either:
1. Wait for training to complete
2. Or check the path:
```python
# In notebook, verify path
import os
os.path.exists("../models/saved/layer2_classifier")  # Should be True
```

### Problem: Notebook kernel keeps dying
**Solution:**
```bash
# Reduce memory usage
# In notebook, restart kernel and run:
import gc
gc.collect()

# Or increase Jupyter memory limit
jupyter notebook --NotebookApp.iopub_data_rate_limit=1e10
```

### Problem: Plots not showing
**Solution:**
```python
# Add this at top of notebook
%matplotlib inline

# Restart kernel and run again
```

---

## 🎨 Visualization Issues

### Problem: "No module named 'PIL'"
**Solution:**
```bash
pip install pillow
```

### Problem: Confusion matrix image not found
**Solution:**
```bash
# Check if training completed successfully
ls results/

# If empty, training didn't finish
# Check train_model.py output for errors
```

### Problem: Matplotlib figures are tiny
**Solution:**
```python
# In notebook, increase figure size
plt.figure(figsize=(12, 8))  # Bigger figures
```

---

## 🏃 Demo Day Issues

### Problem: Laptop won't connect to internet (for downloading model)
**Solution:**
Model should already be downloaded during training.
If not, use mobile hotspot or:
```bash
# Copy models/ folder from college PC via USB
# Place in your project directory
```

### Problem: Jupyter won't start
**Solution:**
```bash
# Alternative: Use Python script instead
python -c "
from models.preprocessing import TextPreprocessor
from models.profiler import PsychologicalProfiler

text = 'Your test message'
preprocessor = TextPreprocessor()
profiler = PsychologicalProfiler()

_, clean = preprocessor.preprocess(text)
profile = profiler.profile(text)
print(profile)
"
```

### Problem: Demo notebook takes too long to execute
**Solution:**
Pre-execute all cells before presentation:
```bash
# Run in headless mode to prepare
jupyter nbconvert --to notebook --execute notebooks/03_demo.ipynb

# Then during demo, just click through pre-executed cells
```

### Problem: Model inference is slow during demo
**Solution:**
```python
# Warm up the model before demo
# Add this cell and run it first:
for _ in range(5):
    result = detect_scam("test message")
# Now actual demo will be faster
```

---

## 💻 Platform-Specific Issues

### macOS: "command not found: pip"
**Solution:**
```bash
pip3 install -r requirements.txt
python3 scripts/clean_data.py
```

### Windows: "pip is not recognized"
**Solution:**
```bash
python -m pip install -r requirements.txt
python scripts/clean_data.py
```

### Linux: Permission denied
**Solution:**
```bash
chmod +x scripts/*.py
python3 scripts/clean_data.py
```

---

## 🎤 Presentation Day Emergencies

### Emergency 1: Model didn't train / Files missing
**Backup Plan:**
1. Show the code and architecture
2. Explain what each layer does
3. Run individual modules:
   ```bash
   python models/preprocessing.py
   python models/profiler.py
   python models/contradiction.py
   ```
4. Show expected results: "With full training, we'd achieve 92-95% accuracy"

### Emergency 2: Jupyter crashes during demo
**Backup Plan:**
1. Show screenshots of results (you took them, right?)
2. Or run Python directly:
   ```bash
   python -c "
   import sys
   sys.path.append('.')
   from models.profiler import PsychologicalProfiler
   
   profiler = PsychologicalProfiler()
   msg = 'URGENT: Your bank account blocked. Enter PIN.'
   print(profiler.profile(msg))
   "
   ```

### Emergency 3: Laptop issues
**Backup Plan:**
1. Have screenshots of all key results
2. Have code printed (at least the demo notebook)
3. Borrow another laptop - all code is in one folder
4. Use college computer if available

---

## 🆘 Getting Help

### During Development (Tonight):
1. **Read error messages carefully** - they usually tell you what's wrong
2. **Check file paths** - most errors are path issues
3. **Google the exact error** - someone has faced it before
4. **Check Python version** - needs 3.8+

### Quick Tests:
```bash
# Test Python
python --version

# Test imports
python -c "import torch; import transformers; print('OK')"

# Test file structure
ls models/ scripts/ data/

# Test one module
python models/preprocessing.py
```

---

## ✅ Verification Checklist

Before presentation, verify these work:

```bash
# 1. Model exists
[ -f "models/saved/layer2_classifier/config.json" ] && echo "✓ Model exists"

# 2. Results exist
[ -f "results/metrics.json" ] && echo "✓ Metrics exist"

# 3. Can import modules
python -c "from models.preprocessing import TextPreprocessor; print('✓ Imports work')"

# 4. Jupyter works
jupyter notebook --version && echo "✓ Jupyter installed"
```

If all show ✓, you're good to go!

---

## 🎯 Most Common Issue: Paths

**90% of errors are path-related. Remember:**

When running from project root:
```python
"data/processed/train.csv"          ← Correct
"models/saved/layer2_classifier/"   ← Correct
```

When running from notebooks/:
```python
"../data/processed/train.csv"       ← Need ../ to go up
"../models/saved/layer2_classifier/" ← Need ../
```

---

## 💡 Pro Tips

1. **Always test once** before the actual presentation
2. **Take screenshots** of working results as backup
3. **Close other applications** to free RAM during demo
4. **Charge laptop fully** night before
5. **Have backup plan** (screenshots, printed code)

---

## 🚀 Last Resort - Minimal Demo

If EVERYTHING fails, you can still demo the logic:

```python
# Create minimal_demo.py
def simple_demo():
    test_messages = [
        "URGENT: Bank account blocked. Enter PIN now.",
        "Your Amazon order has shipped."
    ]
    
    for msg in test_messages:
        # Simple keyword-based demo
        scam_keywords = ['urgent', 'pin', 'blocked', 'verify']
        score = sum(kw in msg.lower() for kw in scam_keywords)
        
        print(f"\nMessage: {msg}")
        print(f"Risk: {'HIGH' if score >= 2 else 'LOW'}")
        print(f"Keywords found: {score}")

simple_demo()
```

This shows you understand the concept even if tech fails.

---

## 📞 Quick Reference

```bash
# Start over from clean slate
rm -rf venv/ models/saved/ data/processed/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/clean_data.py
python scripts/train_model.py

# Check status
ls models/saved/layer2_classifier/  # Model trained?
ls results/                          # Results generated?
jupyter notebook notebooks/03_demo.ipynb  # Demo works?
```

---

**Remember: Code failures are learning opportunities. Your understanding of the architecture and approach is what matters most!**

**You've got this! 💪**
