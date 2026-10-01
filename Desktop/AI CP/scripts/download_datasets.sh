#!/bin/bash

# Dataset Download Script for AI Scam Detection Project
# This script helps download the required datasets

echo "=================================================="
echo "    AI Scam Detection - Dataset Setup"
echo "=================================================="
echo ""

# Create directories
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/synthetic

echo "✅ Directories created"
echo ""

# Dataset 1: Kaggle SMS Spam Collection
echo "📊 Dataset 1: Kaggle SMS Spam Collection"
echo "------------------------------------------------"
echo "This is the primary dataset for training."
echo ""
echo "Option A - Download Manually (RECOMMENDED):"
echo "1. Go to: https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset"
echo "2. Click 'Download' button (requires Kaggle account - free)"
echo "3. Extract spam.csv from the ZIP file"
echo "4. Place spam.csv in: data/raw/spam.csv"
echo ""
echo "Option B - Use Kaggle API (if you have it configured):"
echo "   kaggle datasets download -d uciml/sms-spam-collection-dataset"
echo "   unzip sms-spam-collection-dataset.zip -d data/raw/"
echo "   mv data/raw/spam.csv data/raw/spam.csv"
echo ""

# Check if user wants to try Kaggle API
read -p "Do you have Kaggle API configured? (y/n): " use_kaggle_api

if [ "$use_kaggle_api" = "y" ]; then
    echo ""
    echo "Attempting to download via Kaggle API..."
    
    # Check if kaggle command exists
    if command -v kaggle &> /dev/null; then
        kaggle datasets download -d uciml/sms-spam-collection-dataset
        
        if [ -f "sms-spam-collection-dataset.zip" ]; then
            unzip -q sms-spam-collection-dataset.zip -d data/raw/
            rm sms-spam-collection-dataset.zip
            echo "✅ Kaggle dataset downloaded successfully!"
        else
            echo "⚠️  Download failed. Please download manually."
        fi
    else
        echo "❌ Kaggle CLI not installed."
        echo "   Install: pip install kaggle"
        echo "   Configure: https://github.com/Kaggle/kaggle-api#api-credentials"
    fi
else
    echo "Please download the dataset manually from the link above."
fi

echo ""
echo "=================================================="
echo "✅ Dataset setup instructions complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. If you haven't yet, download spam.csv to data/raw/"
echo "2. Or just run: python scripts/clean_data.py"
echo "   (It will create sample data if spam.csv not found)"
echo ""
