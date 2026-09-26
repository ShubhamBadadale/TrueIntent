# TrueIntent Known Limitations

Stated explicitly per `PROJECT_SPEC.md` §12 — credibility over overselling. Part A carries over the
spec's four items; Part B adds issues **actually observed during implementation and testing**;
Part C records spec items deferred with no implementation.

## Part A — From the spec (§12, still true)

1. **No passive WhatsApp/Telegram scanning (E2E encryption).** The system is evidence-submission based
   (paste text, upload screenshot, paste link) by design and necessity — it cannot see inside encrypted chats.
2. **No live voice/deepfake detection.** Out of scope; future work only. A scammer's live voice call is
   represented by a manual flag or optional Android cellular call-state report. Neither detects scam content or caller intent.
3. **Behavioral text coverage is inadequate.** Module C now has real text, but only five
   cited fear/authority excerpts. The trained classifier misses all five out of fold.
4. **Calm coercion and paraphrases remain unvalidated.** Keyword safeguards still miss
   alternate wording; learned classification does not solve the fear coverage gap.

## Part B — Discovered during implementation and testing

### B.1 ? Module A now uses hybrid data; simulation gains are not real performance
The old F1=1.0 came from disjoint synthetic amount ranges and is superseded.
IEEE-CIS provides all 590,540 real amounts/labels; time and velocity are proxies.
Call state and device novelty are synthetic in every row, conditioned on labels,
then independently bit-flipped with probability 12.5%. Priors are hypothetical.
Chronological holdout: precision 0.0881, recall 0.6863, F1 0.1562, FPR 0.2531.
Without synthetic telemetry: recall 0.5723; delta +11.39 percentage points.
This gain reflects injected assumptions, not observed coercion detection. Poor
precision/high FPR and uncalibrated class-weighted scores limit use. **Do not
present these metrics as real-world performance.** Full details: [datasheet](../data/DATASHEET.md).

### B.2 — Module B has a historical classifier; rule/blend thresholds remain unvalidated
- The typosquatting similarity cutoff (**0.78**) and rule weights were chosen by judgment, never tuned:
  classifier-only evaluation does not validate the rule weights or 50/50 blend thresholds.
- Short brand tokens matched by substring (e.g. `sbi`) can collide with unrelated domains; legitimate
  long URLs (> 75 chars, e.g. share links with tokens) always take a +0.10 length penalty, and any
  `http://` URL takes +0.20 — so plain `http://example.com/` scores **0.2** (Low, but non-zero noise).

  That 0.2 example describes the rules-only fallback; active inference also includes the classifier.
- Phase 1 (2026-09-25): TF-IDF char 3–5 grams + Logistic Regression trained on **real May 2020 URLs**
  from Hannousse/Yahiouche's Web page Phishing Detection dataset (Kaggle v2, CC BY 4.0).
  No synthetic rows/features enter this model. After lowercase-text deduplication, 11,427 rows
  remain; 9,141 train / 2,286 held out, stratified seed 42. Precision **0.9173**, recall **0.9029**,
  F1 **0.9101**, FPR **0.0814** describe the classifier, not the blended score.
- Results are not suspiciously perfect. They are also **not evidence of current real-world performance**:
  452 hostnames occur in both splits, affecting 805 test rows. Near-duplicate paths, shared domains
  and campaigns can inflate the random holdout. No domain-disjoint or temporal evaluation was done.
  Balanced historical prevalence differs from deployment, and calibrated probabilities are not claimed.
- Modern short-link, IDN and Indian banking/UPI campaign coverage is unverified; no per-type recall
  has been measured. The URL-only model does not learn the source's page-content features.
- No current PhishTank supplement: bulk downloads are documented, but its terms now reference Cisco
  terms and mark older permissions archived; current ML-training permission is unclear. See
  [data provenance and source links](../data/README.md#module-b-verified-source-and-reproduction-2026-09-25).
- An absent, unreadable or incompatible model falls back to rules. `ml_status: active` is emitted
  only after successful classifier inference. The backend caches artifacts, so restart after retraining.

The local B artifact records sklearn 1.7.1 while the backend uses 1.7.2; loading
emits a version warning. Tests pass, but cross-version artifact compatibility is
not guaranteed. A future B rebuild should use the pinned backend environment.

### B.3 - Module C trained, but fear/authority fails held-out evaluation
The assembled set has 4,501 ham, 3,190 greed/opportunity and only **5 fear** examples.
Four fear examples are reported fragments rather than verbatim caller transcripts;
one is a reported caller quotation. No invented padding. Greed labels map a real
419 corpus and prize-related source spam to behavior labels; they are weak labels,
not an independent behavioral gold set. Five-fold OOF fear precision/recall/F1 are
**0/0/0**, support 5. Greed F1 **0.9918** and ham F1 **0.9937** are optimistic because
source style and label-selection patterns can make the task easy. Macro F1 **0.6618**.
Existing keyword safeguards and 50/50 blend remain, so metrics are classifier-only.
Class weighting cannot fix absent diversity. Hindi/Hinglish, calm threats, genuine
advisories quoting threats, modern investment scams and OCR noise lack adequate
coverage. No deployment accuracy is established. See [Module C datasheet](../data/MODULE_C_DATASHEET.md).

### B.4 ? Module A no longer has a deterministic synthetic amount boundary
The former low-amount blind-spot demonstration is historical, not a guarantee about
this model. Six coarse features, card-fraud domain shift, relative-hour and customer
proxies, and simulated telemetry leave coercion detection unvalidated. Phase 3
updated the old demo-tier assertions to measured outcomes; A was not tuned to demos.

### B.5 - Learned Module D uses synthetic policy labels
The logistic scorer replaces fixed weights when its artifact exists. Its 2,000
joint scenarios are synthetic independent pairings with an OR-of-positive-source
label policy, not observed joint incidents. C scores are in-sample; component reuse,
weak labels and synthetic A telemetry make evaluation optimistic. P/R/F1=0.8855,
FPR=0.2174 on 400 held-out scenarios. Do not present these metrics as real-world
performance. Missing scores are zero; missing-model fallback alone uses original
A=.45/B=.25/C=.30 weights. See [datasheet](../data/MODULE_D_DATASHEET.md).

### B.6 ? No measured deployment device history
The new artifact has empty device_counts: IEEE-CIS does not establish deployment
device novelty. Existing explicit is_new_device inference works; the unchanged
device_id fallback treats supplied IDs as unfamiliar. Runtime history is not updated.
Training novelty is hypothetical, not inferred from real DeviceInfo descriptions.

### B.7 — OCR paths are contract-tested, not engine-tested
No Tesseract binary exists in this environment, so real OCR accuracy (especially on Hindi/Hinglish or
low-contrast screenshots) is unmeasured; the 20-char/3-word "enough text" heuristic is unvalidated.
English-only keywords additionally exclude large parts of the Indian user base from text protection.

### B.8 — Demo-grade hardening
No database (nothing persisted — good for privacy, bad for audit/feedback loops), no auth, no rate
limiting, no human-feedback loop (spec §9's optional loop is unimplemented). Frontend has no automated
tests (verified by build + live requests only). Timestamps rely on client input; `is_active_call` is
client-reported (manual or Android) and trivially gameable. Freshness and device-ID checks are not authentication.

## Part C — Spec items with no implementation (deferred, not hidden)

- **SQLite persistence** (spec §7): nothing is stored server-side at all.
- **React Testing Library suite** (spec §7): not configured.
- **Docker packaging** (spec §7, optional): implemented (`docker compose up --build` serves
  :5173 to :8000), but its legacy build-time training assumes synthetic A data.
  Not revalidated after upgrades; use native setup with generated artifacts.
- **LIME fallback** (spec §5/§10 "SHAP (or LIME as fallback)"): only heuristic fallbacks exist.
- **WHOIS / domain-age lookup** (implied by the spec §10 example phrase "registered recently"):
  never implemented — Module B judges domains by structure and destination content only, so a
  freshly-registered lookalike domain and a compromised old domain score the same on that axis.
- **Security-header inspection** (spec §5 "basic security headers"): not implemented — destination
  analysis covers redirect chains and login-form presence only.
- **Real jointly labeled incident evaluation, calm-message false-negative study and D ablation**:
  not completed. Synthetic policy evaluation does not fill this gap.

## Android companion scope
Activity-only course demo, not a hardened telemetry pipeline. No background/foreground
service, overlay detection, AccessibilityService, MediaProjection, attestation or mTLS.
READ_PHONE_STATE observes cellular state on the default subscription, not arbitrary
VoIP apps. Manual fallback remains. See [scope and validation](ANDROID_COMPANION.md).
