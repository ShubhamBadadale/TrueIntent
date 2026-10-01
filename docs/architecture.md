# TrueIntent System Architecture

As-built description. Where it differs from `PROJECT_SPEC.md`, the deviation is deliberate and
recorded here and in [`MODULE_A_CORRECTNESS.md`](MODULE_A_CORRECTNESS.md) / ADR-006.

## Topology

```text
                        ┌─────────────────────────┐
                        │      Frontend (UI)       │
                        │  React — 4 input views   │
                        └────────────┬─────────────┘
                                     │ REST calls
                        ┌────────────▼─────────────┐
                        │     API Layer (FastAPI)  │
                        └──┬──────────┬────────┬───┘
                                   │          │   │
              ┌────────────────────▼──┐  ┌────▼────▼───┐
              │ Module B              │  │ Module C    │
              │ URL Checker           │  │ Msg/OCR     │
              │ (rules + TF-IDF LR)   │  │ Analyzer    │
              └───────────────┬───────┘  └──────┬──────┘
                              │  embedded URL     │
                              └────────┬──────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │  Module D — Unified Scorer +  │
                        │  Explanation (logistic,       │
                        │  availability-aware)          │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │  Response: tier, risk index,  │
                        │  plain-language why           │
                        └──────────────────────────────┘

  Module A — amount-only IEEE-CIS benchmark
        └─ standalone endpoint; NOT an input to Module D
```

## System Modules

### Module A: Amount-only source-unit benchmark
- **Input**: `amount` plus an explicit `amount_unit` (`ieee_cis_source`). Optional `timestamp`,
  `device_id`, `is_active_call`, `transaction_velocity` and `call_telemetry` are validated legacy
  metadata and never model features.
- **Model**: XGBoost on a single feature, versioned artifact contract enforced by
  `validate_artifact()`.
- **Output**: `{score, analysis_scope, explanation}` — an uncalibrated benchmark score with a
  mandatory scope notice.
- **Not an input to Module D.** Transaction-bearing `/check-combined` requests are refused.

### Module B: Link/URL Safety Checker
- **Input**: user-supplied URL, parsed offline by `ml/features_module_b.py` (scheme/host validation,
  IDNA, bundled public-suffix list with downloads disabled).
- **Checks**: insecure protocol, raw IP host, brand typosquatting/substring spoofing, high-risk
  TLDs, `@`/hyphen/percent obfuscation, excessive length. Then a 50/50 blend with the trained
  character TF-IDF classifier.
- **Never** fetches the destination: no redirect chain, no page content, no headers, no WHOIS.
- **Output**: `{score, reasons, ml_status}`.

### Module C: Message/Screenshot Scam Analyzer
- **Input**: pasted text, or an image processed by Tesseract OCR (with the documented
  `ocr_status` failure contract and `TESSERACT_CMD` override).
- **Checks**: a ten-class intent model over word + character TF-IDF with logistic regression, plus a
  two-class psychology compatibility model used for explanation wording. Keyword lists are retained
  only as labelled evidence and never override a score.
- **Folding**: URLs found in the text are scored by Module B and folded in as
  `max(text_score, url_score)`, with `text_score` and `embedded_url_score` reported separately so
  Module D can count the link once.
- **Output**: `{score, signature, reasons, ml_status, intent, intent_probabilities, rule_evidence,
  text_assessed, ocr_text?, ocr_status?}`.

### Module D: Unified Risk Scoring & Explanation Layer
- **Input**: Module B and Module C results (Module A never contributes), plus an optional
  user-reported call state.
- **Logic**: a `format_version: 2` logistic policy over fourteen features — three channel scores,
  three presence flags, `active_call` and `call_known`, two tactic signals, and four presence-gated
  cross-channel interactions. Tiers at 0.25 / 0.50 / 0.75. All-`None` raises rather than returning a
  verdict. When no artifact exists, fixed weights A 0.45 / B 0.25 / C 0.30 are renormalized over the
  modules that actually ran, and the response labels that fallback.
- **Explainability**: exact coefficient products (the linear-SHAP attribution against a zero
  reference) rendered as plain-language factors, plus an explicit statement that interactions are
  not independent causal effects.
- **Honesty rules**: contributing and skipped modules are always both listed; a skipped module is
  never implied to have run; a shared URL folded into Module C is not double-counted.

### Module E: Web Portal
- **Framework**: React 19 + Vite 8 + Tailwind 4.
- **Views**: Combined Fraud Analysis (default), Check a Link, Check a Message/Screenshot, and the
  Transaction Benchmark.
- **Results view**: tier badge, Risk Index labelled as uncalibrated, reasons, safety action, and an
  explicit "Not assessed"/"Unavailable" state wherever evidence could not be evaluated.
- **Tests**: `node --test` rendering the real components through `react-dom/server` against a mocked
  `fetch`. Not browser end-to-end.

## API layer

Two route generations share one service layer (`backend/app/services.py`):

| Generation | Routes | Contract |
|---|---|---|
| v1 (current) | `/api/v1/analyze/url`, `/analyze/message`, `/analyze/image`, `/analyze/combined`, `/module-a/benchmark`, `/module-a/contract` | Envelope: `{"success", "data", "meta"}` / `{"success": false, "error", "meta"}`. Full reference: [`API_V1.md`](API_V1.md) |
| legacy (frozen) | `/check-url`, `/check-message`, `/check-transaction`, `/check-combined` | Original flat bodies and `{"detail": …}` errors, byte for byte |

Supporting modules: `config.py` (`TRUEINTENT_*` environment), `errors.py` (stable error codes),
`services.py` (analysis), `validation.py` (URL limits, MIME magic-byte checks, bounded reads),
`diagnostics.py` (readiness probes), `health.py` (`/`, `/health`, `/ready`), `middleware.py`
(request IDs, access log, request-size gate), `observability.py` (structured logging),
`envelope.py`, `safety.py` (response redaction), `v1_schemas.py`, `v1_routes.py`,
`legacy_routes.py`. The single start command is `python -m backend` (`backend/__main__.py`).

## Cross-cutting properties

| Property | How it is enforced |
|---|---|
| No outbound network at serving time | `fetch_live_page=False` at every call site; `tldextract` downloads and cache disabled; `inspect_live_page()` is a no-network stub |
| Honest unavailability | 503 with a reason when a model or the OCR engine is missing; `ml_status` distinguishes `active` from `rules_only`/`unavailable`; `text_assessed` is never inferred |
| Deterministic responses | No randomness at serving time; artifacts cached by `(path, mtime, size)` so retraining requires a restart |
| Bounded input | 20,000 characters of text, 8,192 characters of URL, 10 MB per image, PNG/JPEG/WebP/BMP only, 10 megapixels |
| Privacy by design | Nothing persisted server-side; `data/raw/*` and `*.pkl` gitignored; no screenshots or transaction PII committed |
| Single app identity | `backend.app.main` is imported as a package so there is one app and one model cache |