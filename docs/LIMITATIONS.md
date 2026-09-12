# TrueIntent Known Limitations

Stated explicitly per `PROJECT_SPEC.md` §12 — credibility over overselling. Part A carries over the
spec's four items; Part B adds issues **actually observed during implementation and testing**;
Part C records spec items deferred with no implementation.

## Part A — From the spec (§12, still true)

1. **No passive WhatsApp/Telegram scanning (E2E encryption).** The system is evidence-submission based
   (paste text, upload screenshot, paste link) by design and necessity — it cannot see inside encrypted chats.
2. **No live voice/deepfake detection.** Out of scope; future work only. A scammer's live voice call is
   represented solely by the user-ticked `is_active_call` flag, which is self-reported, not detected.
3. **Message/screenshot datasets are absent, not small.** The spec expected small/partially-synthetic data;
   reality is starker: no Module B/C datasets exist at all, so both run non-ML fallbacks (Part B.2).
4. **Rule/keyword components under-perform on calm, well-scripted scam dialogue.** Confirmed by design:
   zero keyword hits scores **0.0** regardless of context — see Part B.3. This is an open research gap.

## Part B — Discovered during implementation and testing

### B.1 — Module A's perfect metrics are a synthetic-data artifact (do not cite as performance)
Retraining on the committed seed reproduces Precision/Recall/F1 **1.0000**, FPR **0.0000** (60-sample holdout).
This is not model quality: legitimate amounts (₹100–12,000) and fraud amounts (₹15,000–150,000) do not
overlap, so the model is effectively an amount threshold. Verified live: the same daytime/known-device
transfer scores **0.0066** at ₹500 and **0.9889** at ₹45,000. Treat all Module A numbers as
schema-validation evidence only.

### B.2 — Modules B/C are rules-only, with unvalidated thresholds
- The typosquatting similarity cutoff (**0.78**) and rule weights were chosen by judgment, never tuned:
  there are no labeled URLs to validate against, so false-positive/false-negative rates are unknown.
- Short brand tokens matched by substring (e.g. `sbi`) can collide with unrelated domains; legitimate
  long URLs (> 75 chars, e.g. share links with tokens) always take a +0.10 length penalty, and any
  `http://` URL takes +0.20 — so plain `http://example.com/` scores **0.2** (Low, but non-zero noise).

### B.3 — Keyword baseline misses paraphrase and calm coercion
Any rewording outside the 28 hardcoded phrases scores nothing (e.g. polite "please complete KYC"
pressure with no scary words → 0.0/`none`). The Module C ML path (TF-IDF + Logistic Regression) exists
in code but has never run on real data — its SHAP token attribution in Module D is dormant.

### B.4 — Small coerced transfers are invisible to Module A alone
Verified: ₹8,000 daytime transfer on a known device **with an active call** still scores ~0.01 (Low).
The call flag cannot rescue a below-threshold amount. This is the exact blind spot Module D exists to
close (`tests/test_integration.py` proves Low → Medium escalation once the coercive message is
correlated) — but a transaction-only check will miss it.

### B.5 — Module D renormalization dilutes as well as escalates
Because weights renormalize over contributing modules, adding benign inputs lowers a scary score
(e.g. a Critical single-module signal plus two clean inputs averages down to Medium). This is the
documented cost of the single-check-spans-0–1 design (ADR-005); reviewers should know the unified
tier is consensus-like, not max-like.

### B.6 — Device history is frozen at training time
`is_new_device` compares against `device_counts` baked into `module_a.pkl`. Inference never updates
counts, so every never-seen device is "new" forever and compromised known devices never age out.
A production system needs a live device-history store.

### B.7 — OCR paths are contract-tested, not engine-tested
No Tesseract binary exists in this environment, so real OCR accuracy (especially on Hindi/Hinglish or
low-contrast screenshots) is unmeasured; the 20-char/3-word "enough text" heuristic is unvalidated.
English-only keywords additionally exclude large parts of the Indian user base from text protection.

### B.8 — Demo-grade hardening
No database (nothing persisted — good for privacy, bad for audit/feedback loops), no auth, no rate
limiting, no human-feedback loop (spec §9's optional loop is unimplemented). Frontend has no automated
tests (verified by build + live requests only). Timestamps rely on client input; `is_active_call` is
self-reported and trivially gameable.

## Part C — Spec items with no implementation (deferred, not hidden)

- **SQLite persistence** (spec §7): nothing is stored server-side at all.
- **React Testing Library suite** (spec §7): not configured.
- **Docker packaging** (spec §7, optional): implemented (`docker compose up --build` serves
  :5173 → :8000, verified from a fresh clone); native setup remains via `setup.ps1`/`setup.sh`.
- **LIME fallback** (spec §5/§10 "SHAP (or LIME as fallback)"): only heuristic fallbacks exist.
- **WHOIS / domain-age lookup** (implied by the spec §10 example phrase "registered recently"):
  never implemented — Module B judges domains by structure and destination content only, so a
  freshly-registered lookalike domain and a compromised old domain score the same on that axis.
- **Security-header inspection** (spec §5 "basic security headers"): not implemented — destination
  analysis covers redirect chains and login-form presence only.
- **Precision/Recall/F1/FPR for the unified score, false-negative study on calm messages, Module D
  ablation** (spec §11): not yet measurable without labeled B/C data — the evaluation section of the
  final report should own this gap explicitly.
