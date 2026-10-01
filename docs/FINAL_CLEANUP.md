# Practical final cleanup

> Historical phase record, superseded by [`AUDIT_REPORT.md`](AUDIT_REPORT.md), which documents the
> later repository-wide audit. The measurements below are accurate for that phase.

No architecture redesign or model retraining was performed. Existing model metrics
remain historical evaluation results; these changes do not establish a detection
accuracy improvement.

## Changes and files

| Files | Cleanup |
| --- | --- |
| `backend/app/main.py`, `backend/app/schemas.py` | Shared URL parser, malformed URL errors, URL/text length limits, bounded upload reads, OCR/text inference off the async event loop, explicit unassessed OCR responses |
| `ml/model_loading.py`, `ml/predict_module_b.py`, `ml/predict_module_c.py` | Shared artifact validation/cache with replacement/deletion detection; nonfinite B outputs fall back explicitly; canonical brand subdomains no longer trigger impersonation; deduplicated case-insensitive embedded URL extraction |
| `ml/predict_module_b.py` | Live fetch compatibility stub makes no network requests, including when explicitly requested; removes SSRF-capable implementation |
| `ml/ocr_module_c.py` | Actual image format validation, rejects animation and images above 10 million pixels, loads pixels to reject corrupt data, 15-second OCR timeout, explicit missing assessment |
| `ml/predict_module_d.py` | URL credential-symbol evidence no longer described as an observed destination login form |
| `frontend/src/api.js`, `frontend/src/components/MessageCheck.jsx` | Text/upload validation, invalid score rejection, prevents switching input mode during pending analysis |
| `frontend/src/components/Results.jsx`, `frontend/src/components/CombinedResults.jsx` | Risk Index wording, probability caveat, unassessed/invalid scores never rendered as Low, call-context wording |
| `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.dockerignore` | Python 3.11, OCR/OpenMP runtime, nonroot users, no build-time training, read-only model mount, localhost ports, bounded healthcheck, excludes environments/artifacts/secrets from build context |
| `tests/test_cleanup.py`, `frontend/tests/module-a.test.mjs` | Regression tests for hostile URLs, offline fetch, image limits, OCR timeout/abstention, resource limits, model cache changes, score validity and tier boundaries |
| `README.md`, `docs/FINAL_CLEANUP.md` | Current module contracts, Docker setup and cleanup evidence |

## Verification

- Full ml suite: `.venv\Scripts\python.exe -m pytest tests -q`:
  **149 passed, 2 skipped**, two existing dependency deprecation warnings.
  Baseline before cleanup: 135 passed, 2 skipped.
- Frontend: `npm test`: **14 passed** (baseline 12).
- Frontend: `npm run build`: **passed**.
- `git diff --check`: passed; Windows line-ending notices only.
- Docker executable unavailable: build and runtime were **not verified**.
- Two real OCR tests remain skipped because local OCR prerequisites/fixtures are
  absent. Mocked OCR and image boundary tests passed.

## Reviewed contracts and remaining limits

- Training/inference feature modules and fitted pipelines remain shared. No feature
  representation or artifact was retrained in this cleanup. The brand-rule correction
  changes B's heuristic component; it has correctness tests, not a new accuracy estimate.
- Transaction timestamps remain display-only local values in Combined Analysis;
  they are not converted to UTC or used as model features. Existing timestamp and
  Module A source-unit contract tests pass. INR transactions remain unassessed.
- Risk tiers still use policy cutoffs 0.25/0.50/0.75, not validated fraud probabilities.
  Existing backend tests and added frontend boundary tests cover those cutoffs.
- Module C has very sparse real authority/fear/digital-arrest and Hindi/Hinglish
  coverage. Module D learns synthetic policy labels, not observed fraud outcomes.
- Models must be trusted: joblib deserialization is not safe for untrusted artifacts.
  `/health` means API liveness, not that every detector is ready.
- Upload reads and decoded images are bounded, but multipart parsing happens before
  the route handler. A public deployment still needs ingress body/concurrency limits
  and rate limiting. Vite preview remains a local-demo server.
- OCR still uses the installed default language; no Hindi OCR accuracy claim.
- Frontend tests exercise workflow logic and server-rendered components, not a full browser.

## Recommended next three improvements

1. Collect provenance-tracked real scam examples, particularly authority/fear and
   Hindi/Hinglish, plus real paired cross-channel cases; retain seed/domain-disjoint
   holdouts before changing thresholds or claiming better detection.
2. Add CI with a Docker smoke test, actual Tesseract fixtures and browser end-to-end
   tests for combined analysis, missing models and unreadable screenshots.
3. Before public deployment, add ingress body/rate/concurrency limits and model
   readiness reporting; use production static hosting instead of Vite preview.
