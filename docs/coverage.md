# TrueIntent Test Coverage Report

- **Date**: 2026-09-12
- **Environment**: Windows (win32), Python 3.10.9, `backend/venv`
- **Result**: **43 passed, 2 skipped** (skips: real-screenshot evidence tests awaiting
  user-provided screenshots / Tesseract binary — see `tests/test_module_c_ocr.py`)
- **Reproduce**: from repo root,
  `.\backend\venv\Scripts\python.exe -m pytest tests/ --cov=ml --cov=backend --cov-report=term-missing -q`

## Per-file coverage (measured, not estimated)

| File | Stmts | Miss | Cover | Notes on uncovered lines |
| :--- | ---: | ---: | ---: | :--- |
| `backend/app/__init__.py` | 0 | 0 | 100% | — |
| `backend/app/main.py` | 122 | 33 | 73% | Live-page-fetch, OCR-503, model-missing branches |
| `backend/app/schemas.py` | 66 | 5 | 92% | Rare validators |
| `ml/__init__.py` | 6 | 0 | 100% | — |
| `ml/generate_module_a_data.py` | 45 | 45 | 0% | One-shot data script, run manually |
| `ml/ocr_module_c.py` | 75 | 20 | 73% | Real-Tesseract paths (no engine binary in CI) |
| `ml/predict_module_a.py` | 55 | 15 | 73% | `__main__` demo, rare timestamp fallbacks |
| `ml/predict_module_b.py` | 139 | 49 | 65% | Live-fetch (option a), trained-ML branches (dataset pending) |
| `ml/predict_module_c.py` | 123 | 48 | 61% | Trained-ML branches (dataset pending), `__main__` demo |
| `ml/predict_module_d.py` | 303 | 99 | 67% | ML token-attribution (no Module C artifact), SHAP fallbacks |
| `ml/train_module_a.py` | 67 | 67 | 0% | Training script, run manually (prints metrics) |
| `ml/train_module_b.py` | 47 | 47 | 0% | Training script (dataset pending) |
| `ml/train_module_c.py` | 130 | 130 | 0% | Training script (dataset pending) |
| **TOTAL** | **1178** | **558** | **53%** | — |

## Headline numbers

- **Serving + inference code only** (excluding one-shot `train_*` / `generate_*`
  scripts, which are executed manually rather than under pytest):
  **~70%** (620/889 statements).
- **End-to-end integration** (`tests/test_integration.py`, 5 tests): URL flow
  coherence with Module B rules, Module C→B URL folding, the Module D
  escalation proof (Low → Medium vs. transaction alone), and frontend→backend
  route wiring — all passing.

## Known gaps (honest limitations, not hidden)

1. ML-combined branches for Modules B/C are untested because no labeled
   datasets (and hence no trained artifacts) exist yet — both run rules-only.
2. Live page fetching (Module B option a) is untested (needs network egress).
3. Real-OCR paths are untested (Tesseract engine binary not installed here);
   mocked + blank-image + heuristic tests cover the pipeline contract instead.
4. Training scripts are verified by running them (they print precision/recall/F1),
   not by pytest assertions.
