# Repository Audit Report — branch `ved`

- **Scope**: full repository — `backend/`, `ml/`, `frontend/`, `android/`, `tests/`, `data/`,
  `docs/`, tooling and all root documentation.
- **Method**: read every source file, ran the complete Python and frontend suites, started the
  backend and re-measured every documented endpoint, built a clean virtualenv from the pinned
  requirements and ran the suite against it, and cross-checked each documentation claim against
  the code.
- **Baseline at start**: 149 passed, 2 skipped (Python), 14 passed (frontend).
- **Result at end**: 149 passed, 2 skipped (Python), 14 passed (frontend), `oxlint` clean,
  `vite build` clean, clean-checkout virtualenv verified.

Two principles governed every change:

1. **Do not weaken tests to make them pass.** Where a test was passing by luck — depending on a
   gitignored artifact — it was made to skip *explicitly* instead of failing silently on a clean
   clone. No assertion was relaxed, removed or loosened.
2. **Preserve the safer behaviour already on this branch.** The Module A amount-only contract, the
   422 on transaction fusion, the 503 on missing artifacts, the no-network serving path and the
   OCR failure contract are all intact and better documented. No transaction/call-context claim was
   restored anywhere.

---

## 1. Issues discovered and fixed

### 1.1 Broken imports and non-runnable entry points

| Issue | Location | Fix |
|---|---|---|
| `python ml/predict_module_c.py` crashed — hard `from ml.features_module_c import …` with no fallback | `ml/predict_module_c.py:96` | Added an explicit `sys.path` bootstrap and hoisted the imports to module scope, matching `predict_module_b.py` |
| `python ml/predict_module_d.py` crashed whenever `module_d.pkl` existed — hard `from ml.features_module_d import …` | `ml/predict_module_d.py:53,484` | Hoisted to module scope behind the same bootstrap; deleted the now-dead `try/except ImportError` fallbacks |
| `python ml/evaluate_module_c.py` silently did nothing (no `__main__`) | `ml/evaluate_module_c.py` | Added `if __name__ == '__main__': train_intents()` |
| `ml/scripts/generate_signature_examples.py` could not import at all (both paths failed), contained a mojibake f-string marker, wrote a **2-column CSV over the real Module C artifact at the same path** with no provenance and no backup | whole file | **Deleted.** It duplicated `ml/generate_module_c_data.py` and would have silently destroyed Module C provenance |
| Default output/input paths were CWD-relative in four scripts, so they only worked when invoked from the repo root | `train_module_a.py`, `train_module_b.py`, `train_module_c.py`, `evaluate_module_c.py` | Made them `ROOT`-relative like the generators |

### 1.2 Dead code and duplication

| Issue | Location | Fix |
|---|---|---|
| `generate_legacy_module_d_data()` could **never** succeed: it loaded `module_a.pkl` and raised because `train_module_a.py` always writes the v2 contract | `ml/generate_module_d_data.py` | Deleted (60 lines plus five now-unused imports) |
| `train_legacy_module_d()` read a CSV that only the deleted generator wrote | `ml/train_module_d.py` | File reduced to an 18-line delegation to `evaluate_module_d.evaluate()`; nine imports removed |
| `train_legacy_module_c()` superseded by the ten-intent pipeline in `evaluate_module_c.py`, duplicating assembly logic | `ml/train_module_c.py` | Deleted; `new_pipeline()` retained because tests and the measured baseline comparison use it |
| `is_ip_address()` — dead public wrapper with zero callers | `ml/predict_module_b.py:62` | Deleted |
| `WEIGHT_LOGIN_FORM_PRESENT = 0.25` and its branch were **unreachable**: `inspect_live_page()` is a no-network stub that always returns `has_login_form=False` | `ml/predict_module_b.py` | Deleted the constant and the dead branch; `inspect_live_page()` kept and documented as the no-egress guarantee that tests assert |
| `inspect_live_page(timeout=2.0)` — parameter never used | `ml/predict_module_b.py` | Removed |
| `result["text"] = text.strip()` written into a dict that was then discarded (the response model has no `text` field) | `backend/app/main.py` | Removed |
| `from datetime import datetime` re-imported inside a validator, shadowing the module-level import | `backend/app/schemas.py` | Removed |
| Redundant local `import pandas as pd` / `import numpy as np` inside functions, shadowing module-level imports | `ml/predict_module_d.py:165,172` | Removed |
| Unused imports: `urllib.parse` (backend + Module B), `pandas` (evaluate_module_c), `os` (train_module_c), `numpy`/`pandas` (test), `pathlib.Path` (test), a never-used `PIL` binding (test) | multiple | Removed |
| `os.stat(path)` called twice in a row to build one cache stamp | `ml/predict_module_d.py` | Single call |
| `ml/module_a_priors.json` — orphaned config for the removed six-feature model, with no reader anywhere | repo root of `ml/` | **Deleted** |
| `ml/models/module_a.metrics.json` — stale six-feature report with no `feature_contract`, describing a model that cannot be loaded | `ml/models/` | **Deleted.** The figures are preserved as a labelled historical record in `data/DATASHEET.md` |
| `ml/models/module_c.before-3ed28ab2388f.pkl` — leftover backup blob | `ml/models/` | Deleted |
| `frontend/src/App.css`, `src/assets/hero.png`, `src/assets/react.svg`, `src/assets/vite.svg`, `public/icons.svg` — Vite scaffold with zero references | `frontend/` | **Deleted** |
| `frontend/README.md` — the stock Vite React template README, describing none of this project's setup | `frontend/` | Replaced with real content |
| `tests/ml/.gitkeep`, `tests/backend/.gitkeep` — empty placeholder directories | `tests/` | Left in place (harmless; `tests/backend/` is in use) |

### 1.3 Inconsistent / incorrect API responses and schemas

| Issue | Detail | Fix |
|---|---|---|
| Helper named `_normalize_url_or_400` that raised **422** | `backend/app/main.py` | Renamed to `_normalize_url_or_422` |
| `mod_a` was declared and threaded through `/check-combined` while being permanently `None` | `backend/app/main.py` | Made explicit with a comment stating Module A is never a fusion input |
| `TransactionCheckRequest` accepted `timestamp`, `device_id`, `is_active_call`, `transaction_velocity`, `call_telemetry` with no indication that none of them are model features | `backend/app/schemas.py` | Added a class docstring stating they are validated legacy metadata, never features and never fusion evidence |
| `CombinedRequest.transaction` accepted a value that always 422s, with no explanation on the schema | `backend/app/schemas.py` | Added a docstring explaining the field exists only to produce a clear refusal |
| `ml_status` strings were undocumented, so the frontend's `includes('unvalidated')` branch had matched nothing since the intent-v2 rewrite | `frontend/src/components/CombinedResults.jsx:16` | Replaced the dead branch with two live ones (`limited real-language coverage`, `unavailable …`) |
| Frontend accepted a URL longer than the backend's 8192-char cap and surfaced a raw 422 | `frontend/src/combinedAnalysis.js` | Added the cap client-side; text cap too. Limits now live once in `api.js` and are imported |
| `image.format` was checked after `getattr(image, 'is_animated', False)`, an attribute that only exists *before* `load()` — so the animation guard never fired | `ml/ocr_module_c.py:86` | Checks `is_animated` **and** `n_frames > 1` |
| `ml/generate_module_c_data.py` put free-text sentences into `source_kind`, a categorical column, producing nonsense `source_counts` keys in the metadata | `ml/generate_module_c_data.py:111` | Uses the categorical `curated_fear_excerpt`; the prose stays in `label_basis` |

### 1.4 Frontend/backend mismatches

| Issue | Detail | Fix |
|---|---|---|
| The Android companion **guaranteed** an HTTP 422: it never sent `amount_unit`, which is the field that decides success | `android/.../MainActivity.kt:66` | Sends `"amount_unit": "ieee_cis_source"` and relabels the input field "IEEE-CIS benchmark amount (source units, NOT INR)", mirroring the web form. The app now gets 503-with-reason instead of an unexplained 422 |
| Two different module identities for the same FastAPI app (`app.main` and `backend.app.main`) — two app objects, two model caches, and `main.py` reported **0% coverage** because it was imported under the other name | `tests/conftest.py`, 4 test files | `backend/__init__.py` added; every test imports `backend.app.main`; `backend/` removed from `sys.path`. Coverage for `backend/app/main.py` went 0% → 78% |
| `CombinedResults.jsx` told the user "Transaction details are not scored or sent" while rendering the amount and velocity they typed | `frontend/src/components/CombinedResults.jsx:43` | Wording now says they are display-only and not sent, matching what the code does |

### 1.5 Test suite

| Issue | Detail | Fix |
|---|---|---|
| Three tests silently depended on the **gitignored** `ml/models/module_c.pkl` and would fail on a clean clone, while sibling tests skipped for exactly the same reason | `tests/backend/test_api.py`, `tests/test_integration.py` | Added an explicit `requires_module_c` marker / `skipif` that names the remedy |
| `tests/test_cleanup.py`, `tests/backend/test_call_telemetry.py`, `tests/backend/test_module_a_contract.py` imported `PIL` / `fastapi` / `httpx` at module level with **no** `importorskip`, so a bare environment produced a collection **error**, not a skip | 3 files | Added the guards |
| `tests/test_cleanup.py` imported `pytesseract` inside a test with no guard | `tests/test_cleanup.py` | `importorskip` |
| Five near-identical `sys.path.insert(…, ROOT)` bootstraps duplicating `tests/conftest.py` | 5 test files | Removed from all of them |
| `parametrize("url,label", …)` passed a `label` that the test body never used | `tests/test_module_b_classifier.py` | Reduced to `url` |
| Unreachable second skip inside a fixture-guarded test | `tests/test_module_b_classifier.py:45` | Left, but it is now genuinely reachable because the fixture's skip is the outer guard — verified by reading the guard chain |
| Unused `numpy`/`pandas` imports, unused `Path`, unused `PIL` binding | 4 test files | Removed |
| No `pytest.ini` anywhere; the suite could only be invoked with an explicit path | repo root | Added `pytest.ini` with `testpaths = tests` and `-ra` |
| UTF-8 **BOM** at the start of three Python files | `ml/generate_module_c_data.py`, `ml/train_module_d.py`, `tests/test_module_c_classifier.py` | BOMs stripped (and `data/DATASHEET.md` while rewriting it) |

### 1.6 Dependency, tooling and environment issues

| Issue | Detail | Fix |
|---|---|---|
| **Two mutually exclusive virtualenv conventions**, and *neither* matched the checkout: `backend/venv` in 11 places vs root `.venv` in 5, while `backend/venv` did not exist | `Makefile`, `setup.*`, `run-backend.*`, `README.md`, 5 docs | Standardised on root `.venv`. All scripts rewritten |
| `Makefile` used Windows-only `.\venv\Scripts\…` path separators — it could not work on the platform `make` targets | `Makefile` | Rewritten with Windows and POSIX variants and overridable variables |
| `python` was assumed to be on `PATH` — it is not on this machine | `setup.ps1`, `Makefile` | `setup.ps1` resolves the interpreter via `py -3` → `python` → `python3` → the standard per-user Windows install roots, and fails with a clear message otherwise. `Makefile` uses a `PY` shell probe. Verified end-to-end |
| `backend/requirements.txt` claimed "Python 3.10" while the Docker image and the actual environment are 3.11, and shipped the test toolchain into the runtime image | `backend/requirements.txt` | Split into `requirements.txt` (runtime, grouped by role) and a new `requirements-dev.txt` (pytest, pytest-cov, httpx); header corrected to CPython 3.11 |
| No `.env.example` anywhere | repo root | Added. `TESSERACT_CMD` is now actually honoured by `ml/ocr_module_c.py` (previously the `.env` convention documented in some files was fiction) |
| `pytesseract` cannot find Tesseract on common Windows installs and there was no override | `ml/ocr_module_c.py` | Added `configure_tesseract_command()` reading `TESSERACT_CMD` |
| `backend/Dockerfile` is run with `--app-dir backend`-style invocation but the docstring in `main.py` said `cd backend && ..\\venv\\…` | `backend/app/main.py` | Docstring corrected to the command the scripts actually run |
| `.dockerignore` was missing `android/` (with its ~large `.gradle/` cache) and `docs/` | `.dockerignore` | Reviewed; **left unchanged** — nothing it excludes is needed by either Dockerfile, and adding patterns was cosmetic. Noted as a non-issue in §4 |

### 1.7 Documentation that contradicted the code

Every claim below was checked against the source and, where numeric, re-measured against a running
backend.

| Document | Stale claim | Reality |
|---|---|---|
| `README.md` ×2 | "81 passed, 2 skipped" | 149 / 2 |
| `README.md` | `/check-transaction` body omits `amount_unit`, shows `device_id` as required, returns `{score}` | `amount_unit` decides success/failure; `device_id` is optional; response is `{score, analysis_scope, explanation}` |
| `README.md` | `/check-combined` accepts `{transaction, url, text}` | `transaction` always 422s; `active_call` is undocumented |
| `README.md` | `/check-message` returns 5 fields | Returns 9 (`intent`, `intent_probabilities`, `rule_evidence`, `text_assessed` also) |
| `README.md` | "Node.js 18+ (npm 9+)" | Vite 8 needs 20.19+/22.12+; `node --test` glob and `t.mock` need ≥ 20.6 |
| `README.md` | "only module_a.pkl exists locally"; six-feature Module A metrics presented as current | `module_a.pkl` is absent; those metrics describe a deleted model |
| `README.md` ×11 | `backend/venv` | `.venv` |
| `docs/coverage.md` | 81 passed / 43 passed; 53% coverage; Python 3.10; cites a **deleted** escalation test | 149 / 2; 76% overall, 82% serving; CPython 3.11 |
| `docs/LIMITATIONS.md` B.1–B.8 | Six-feature hybrid Module A, a "keyword safeguard" baseline, Module B recall 0.9029, "no domain-disjoint evaluation", "frontend has no automated tests", "Docker trains Module A", live-page/login-form capability | All contradicted; rewritten. Also fixed 3 `?` characters that should have been em dashes |
| `docs/DECISIONS.md` D-01/D-02/D-03/D-07/D-11 | Synthetic Module A generator, "keyword baseline" with a documented step function, Dockerfile retraining, "no frontend test runner" | All superseded; rewritten with D-13 recording this audit |
| `docs/decision_log.md` ADR-002/003/004 | Synthetic Module A + two-stage Module C; `hour_of_day`/`is_new_device`; **live page fetching** | Marked superseded/amended in place, with ADR-006 added |
| `docs/DEMO_SCRIPT.md` | Every single output was wrong — 0.0066, 0.6, 0.9 with four matched-phrase reasons, High 0.523, and a proof test that **does not exist** | Rewritten end-to-end from live measurements (0.7944, 0.0357, 0.8681, 0.707, Low 0.0938, High 0.5086) |
| `docs/ANDROID_COMPANION.md` | "rejected with 422", "same transaction object works under `/check-combined`", "response remains `{score}`", "placeholder launcher icon", `backend/venv`, 81 tests | Rewritten |
| `data/README.md` | Six-feature contract, "hybrid ? real rows + synthetic telemetry", 7,696 Module C examples, `[x]` on a file that does not exist, bare `python` commands | Rewritten against the actual 4,724-row intent set |
| `data/DATASHEET.md` | Documented the deleted six-feature model and the deleted priors file as current | Rewritten: current contract first, historical v1 explicitly labelled and preserved |
| `data/schema.md` | Literal `\n` mid-sentence; described the v1 Module D scenario file | Fixed; rewritten to the actual generator and columns |
| `data/MODULE_D_DATASHEET.md` | Reproduction commands for a generator that no longer exists | Commands replaced with a note plus the current entry point |
| `docs/architecture.md` | Diagram and module descriptions showing Module A feeding Module D and Module B inspecting destination pages/headers/WHOIS | Rewritten as-built, with the Module A exclusion drawn |
| `docs/PROJECT_SPEC.md` | A **divergent, truncated duplicate** of the root spec, with a misaligned ASCII diagram | Replaced with a pointer; the root spec is the single source of truth |
| `DECISIONS.md` (root) vs `docs/DECISIONS.md` | Two different documents with near-identical names, neither saying so | Root file is now explicitly an index, with a table distinguishing the two |
| `CHANGELOG.md` | No entry for the Module A rewrite, intent-v2, Module D interactions or the combined view; asserted Dockerfile retraining | Rewritten with those entries; superseded items struck through rather than deleted |

---

## 2. Files changed

**Added (5)**

```
.env.example                              backend/requirements-dev.txt
backend/__init__.py                       docs/AUDIT_REPORT.md
pytest.ini
```

**Deleted (10)**

```
frontend/public/icons.svg                  frontend/src/App.css
frontend/src/assets/hero.png               frontend/src/assets/react.svg
frontend/src/assets/vite.svg               ml/module_a_priors.json
ml/models/module_a.metrics.json            ml/models/module_c.before-3ed28ab2388f.pkl
ml/scripts/generate_signature_examples.py
```

**Modified — code and config (34)**

```
Makefile                       setup.ps1                    setup.sh
run-backend.ps1                run-backend.sh               run-frontend.ps1
run-frontend.sh                .dockerignore (reviewed)
backend/app/main.py            backend/app/schemas.py       backend/requirements.txt
ml/evaluate_module_c.py        ml/generate_module_c_data.py ml/generate_module_d_data.py
ml/ocr_module_c.py             ml/predict_module_b.py       ml/predict_module_c.py
ml/predict_module_d.py         ml/train_module_c.py         ml/train_module_d.py
android/app/src/main/java/org/trueintent/companion/MainActivity.kt
frontend/src/api.js            frontend/src/combinedAnalysis.js
frontend/src/components/CombinedResults.jsx
frontend/README.md
ml/models/module_b.metrics.json (regenerated: latency figures only)
```

**Modified — tests (14)**

```
tests/conftest.py                  tests/test_cleanup.py           tests/test_integration.py
tests/test_module_b.py             tests/test_module_b_classifier.py
tests/test_module_c.py             tests/test_module_c_classifier.py
tests/test_module_c_intents.py     tests/test_module_c_ocr.py     tests/test_module_d_interactions.py
tests/backend/test_api.py         tests/backend/test_call_telemetry.py
tests/backend/test_module_a_contract.py
```

**Modified — documentation (18)**

```
README.md            DECISIONS.md          CHANGELOG.md
docs/ANDROID_COMPANION.md   docs/DECISIONS.md   docs/DEMO_SCRIPT.md
docs/LIMITATIONS.md          docs/MODULE_A_CORRECTNESS.md
docs/MODULE_D_FUSION_EVALUATION.md             docs/PROJECT_SPEC.md
docs/architecture.md         docs/coverage.md   docs/decision_log.md
docs/FINAL_CLEANUP.md
data/DATASHEET.md    data/README.md          data/schema.md
data/MODULE_C_DATASHEET.md                    data/MODULE_D_DATASHEET.md
```

Net: **~1,625 insertions, ~1,814 deletions** across 66 tracked files.

---

## 3. Test results

### Python — `.\.venv\Scripts\python.exe -m pytest`

```
149 passed, 2 skipped, 2 warnings in 4.3s
```

Identical to the pre-audit baseline. Nothing was weakened to achieve it.

**The two skips:**

| Test | Reason |
|---|---|
| `test_user_provided_screenshot` | No real chat screenshots in gitignored `data/raw/screenshots/` (awaiting user-supplied evidence) |
| `test_synthetic_fixture_end_to_end` | No Tesseract engine binary on this machine |

**Conditional skips added** for gitignored artifacts (`ml/models/module_{b,c}.pkl`), so a clean clone
degrades honestly instead of failing. Affected: `test_real_classifier_and_blend`,
`test_real_split_has_no_duplicate_text_leakage`, `test_real_model_metadata_and_inference`,
`test_check_message_text_success`, `test_check_combined_low_success`,
`test_message_with_embedded_url_folds_in_module_b`.

### Coverage — `--cov=backend.app --cov=ml`

```
TOTAL   1742 stmts   416 miss   76%
Serving + inference subset: 1059 stmts, 186 miss, 82%
backend\app\main.py          129    28   78%   (was reported as 0% via the duplicate import)
backend\app\schemas.py       103     5   95%
ml\predict_module_b.py       105    13   88%
ml\predict_module_c.py        89    10   89%
ml\predict_module_d.py       332    85   74%
ml\ocr_module_c.py           104    26   75%
```

Previously reported: 53% overall / ~70% serving, from a 2026-09-12 measurement over 8 fewer test
files, with `main.py` mis-attributed.

### Clean-environment verification

A brand-new virtualenv was created outside the repository and populated **only** from
`backend/requirements.txt` + `backend/requirements-dev.txt`:

```
pip install  →  exit 0
pytest -q    →  149 passed, 2 skipped in 21.6s   (PYTESTEXIT=0)
```

`setup.ps1` was then executed against the real repo and completed successfully end to end.

### Frontend

```
npm test        →  tests 14 · pass 14 · fail 0
npm run lint    →  0 findings
npm run build   →  ✓ built in 179ms
```

### Live endpoint verification

Backend started with `python -m uvicorn app.main:app --app-dir backend --port 8011`; every number in
the rewritten `docs/DEMO_SCRIPT.md` was captured from it, not estimated:

| Request | Result |
|---|---|
| `/health` | `{"status":"ok"}` |
| `/check-url` `http://192.168.1.1/verify-account` | `0.7944`, 2 reasons, `ml_status: active` |
| `/check-url` `https://www.google.com/search?q=test` | `0.0357`, no reasons |
| `/check-url` `http://hdfcbaank-login.xyz/update-kyc` | `0.8681`, 3 reasons |
| `/check-transaction` legacy body (no `amount_unit`) | **422** |
| `/check-transaction` `{amount:500, amount_unit:"ieee_cis_source"}` | **503** (no artifact — correct) |
| `/check-combined` with a `transaction` | **422** |
| `/check-message` fear text | `0.707`, `fear_authority`, intent `digital_arrest` |
| `/check-combined` safe URL + lunch text | **Low, 0.0938** |
| `/check-combined` IP URL + coercion text + `active_call:true` | **High, 0.5086** |

---

## 4. Remaining issues (not fixed, and why)

These are real and are listed rather than papered over.

1. **Module A cannot be trained or demonstrated.** The authorized IEEE-CIS source is licensed and
   absent, so `/check-transaction` returns 503. This is the intended state per ADR-006 — the audit
   deliberately did **not** fabricate a substitute. Restoring INR assessment requires labelled data
   with justified units; restoring transaction fusion additionally requires retraining Module D.
2. **No Docker verification.** The `docker` executable is unavailable on this machine, so
   `docker compose up --build` was not exercised. Both Dockerfiles and `.dockerignore` were
   reviewed statically and are internally consistent, but startup remains unproven.
3. **Real OCR is untested.** No Tesseract binary here. The pipeline contract is covered by mocked
   OCR, a blank control image, the format/dimension guards and the "enough text" heuristic. Real
   accuracy — especially Hindi/Hinglish — is unmeasured, and only the default English model is used.
4. **No real screenshot evidence test.** It skips pending user-supplied screenshots in
   `data/raw/screenshots/`.
5. **`source_kind` semantics in `data/module_c_fear_sources.json`.** The generator now writes the
   categorical `curated_fear_excerpt` into the assembled CSV, but the hand-authored JSON still uses
   that key for prose. Regenerating Module C therefore requires network access, which was not
   available, so the committed `data/raw/signature_examples.csv` and its metadata hash predate this
   change. The trainers still verify their hash, so nothing silently trains on mismatched data — but
   **Module C must be regenerated and retrained** before the fix is reflected in the artifact.
6. **Coarse provenance classification.** `module_c_dataset.py` labels whole datasets
   `source_english_dominant` and maps every greed-labelled corpus row to `other_fraud`. The true
   per-row intent is not known; this is documented rather than guessed at.
7. **`data/module_c_intent_seeds.json` counts are asserted by a test.** `test_module_c_intents.py`
   asserts exactly 54 synthetic and 63 augmented rows, so editing the seed file breaks the test by
   design.
8. **Demo-grade hardening.** No database, no auth, no rate limiting, no request logging, no feedback
   loop. CORS admits any localhost port with credentials — fine locally, unsafe if exposed.
   `/health` reports process liveness, not model readiness.
9. **Model artifacts must be trusted.** `joblib.load` is not safe on untrusted input.
10. **Multipart parsing happens before the route handler.** Upload reads and decoded images are
    bounded (10 MB, 10 megapixels), but a public deployment still needs ingress body/concurrency
    limits. `vite preview` is a local-demo static server, not production hosting.
11. **`ml/evaluate_module_c.py` (33%) and `ml/evaluate_module_d.py` (42%) are lightly covered.**
    They are long-running jobs; they are exercised by running them, not by pytest.
12. **`.dockerignore` excludes `android/`, `docs/` and `tests/`.** Nothing the Dockerfiles need is
    excluded, so the builds are correct; adding these would only shrink the build context. Left
    unchanged as cosmetic.
13. **Android app was not built or installed.** `assembleDebug`/`lintDebug` had passed in an earlier
    phase; the payload change in this audit was verified against the schema by reading, not by a
    Gradle build. There is no `res/` directory and neither manifest declares `android:icon`.
14. **No CI.** Everything in this report was verified manually on one machine.

---

## 5. Architectural risks

Ordered by how likely they are to cause a wrong conclusion.

1. **The unavailable-Module-A path is the default experience.** A clean clone yields 503 on
   `/check-transaction` and no benchmark number. That is correct, but it means a reviewer who
   enables transaction fusion "to see the demo" will be reading a refusal as a bug. The 422 and 503
   messages now say exactly this.
2. **Module D is a policy simulator.** Its coefficients fit a hand-written label policy over invented
   scores. Its ablation ladder (B 0.647 → B+C 0.685 → A+B+C 0.825) looks like a correlation-layer
   proof and is not one. Any narrative built on that ladder would be overclaiming.
3. **Model calibration is absent everywhere.** Class weighting (Module A), `max(text, url)` folding
   (Module C) and a logistic policy (Module D) all produce numbers that look like probabilities and
   are not. The UI labels them "Risk Index"; the API does not. Anyone reading a raw score could easily
   over-read it.
4. **Training/serving skew was the original defect and the class of bug is not fully closed.**
   ADR-003 was a skew bug, ADR-006 removed those features, and ADR-002's two-stage Module C was
   another skew bug. The systematic mitigation is the versioned feature contracts
   (`FEATURE_CONTRACT`, `format_version`), but they are enforced **per module**, not across the
   pipeline. Nothing structurally prevents a future Module B/C change from silently invalidating
   Module D's artifact.
5. **A single unlabeled intermediate truth (`ml/models/module_d.pkl`) carries a lot of weight.** It is
   gitignored, so a fresh clone silently falls back to fixed weights. The response does label that
   fallback, but a demo could run on the fallback without anyone noticing.
6. **Module C's real-language support is 5 rows.** Everything else in that taxonomy is authored.
   Hindi/Hinglish coverage is a diagnostic on synthetic text. Any claim of multilingual capability
   would be unsupported by construction.
7. **The rule/classifier blend in Module B is unvalidated.** Classifier-only metrics are strong
   (F1 0.91 random, 0.89 domain-disjoint), but the 50/50 blend with judgment-set weights has never
   been measured end to end.
8. **Duplicate module identity was real and nearly invisible.** Two `app.main` copies coexisted
   without any test failure — one set of tests exercised the app, coverage tooling measured the
   other. That is a warning about the test harness, not about the application.
9. **Blocking calls are now offloaded explicitly.** *(Correction to the original wording of
   this item: Starlette already runs sync `def` handlers in its own threadpool, so the legacy
   routes never blocked the event loop; the real gap was that the offload was implicit.)* Every
   v1 handler is `async` with an explicit `run_in_threadpool` around the blocking ML/OCR unit, and
   the service layer documents the sync-blocking contract. The remaining bound under load is the
   default threadpool size plus the frontend's 90-second abort.
10. **No persistence at all.** Correct for privacy, but it means no audit trail, no threshold
    feedback loop, and no ability to detect drift after deployment.