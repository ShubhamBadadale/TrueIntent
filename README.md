# TrueIntent — Multi-Channel Fraud Intent Verification System

> Banks verify *who* you are. Nobody verifies *why* you're sending the money. TrueIntent closes that gap.

## Overview

Correlate transaction context + user-submitted evidence into one explainable risk score, instead of checking each signal in isolation.

## Project Structure

```text
├── backend/     # FastAPI app (API layer & business logic)
├── frontend/    # React app (UI dashboard & submission forms)
├── ml/          # Machine learning (training scripts, model artifacts, notebooks)
├── data/        # Data directory
│   ├── raw/        # Raw datasets (excluded from git)
│   └── processed/  # Processed & cleaned datasets
├── tests/       # Test suite
│   ├── backend/    # Backend FastAPI tests
│   └── ml/         # ML model & pipeline tests
├── docs/        # Architecture diagrams, specifications, & decision logs
├── setup.sh / .ps1     # Automated environment setup scripts
├── run-backend.sh / .ps1 # Server startup script for FastAPI
├── run-frontend.sh / .ps1# Dev server startup script for React (Vite)
├── Makefile     # Utility make commands
├── README.md    # Root project documentation
└── .gitignore   # Workspace git ignore configuration
```

---

## System Prerequisites & Dependencies

### 1. System-Level Dependency: Tesseract OCR
> [!IMPORTANT]
> `pytesseract` is a Python wrapper and **requires the Tesseract OCR binary** to be installed natively on your host OS.

| Operating System | Installation Command / Instructions |
|---|---|
| **Ubuntu / Debian** | `sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev` |
| **macOS (Homebrew)** | `brew install tesseract` |
| **Windows (Winget)** | `winget install UB-Mannheim.TesseractOCR` |
| **Windows (Manual)** | Download executable installer from [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki). Ensure `C:\Program Files\Tesseract-OCR` is added to your System PATH environment variables. |

### 2. Runtime Requirements
- **Python**: `3.10` or higher
- **Node.js**: `18.0.0` or higher (with `npm` v9+)

---

## Setup Instructions

### Automated Setup

#### Linux / macOS:
```bash
chmod +x setup.sh run-backend.sh run-frontend.sh
./setup.sh
```

#### Windows (PowerShell):
```powershell
.\setup.ps1
```

#### Using Makefile:
```bash
make setup
```

---

## Running the Application

### 1. Start FastAPI Backend:
```bash
# Linux / Mac:
./run-backend.sh

# Windows (PowerShell):
.\run-backend.ps1

# Makefile:
make backend
```
The API server runs at `http://localhost:8000`. Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 2. Start React Frontend (Vite):
```bash
# Linux / Mac:
./run-frontend.sh

# Windows (PowerShell):
.\run-frontend.ps1

# Makefile:
make frontend
```
The frontend dev server runs at `http://localhost:5173`.
