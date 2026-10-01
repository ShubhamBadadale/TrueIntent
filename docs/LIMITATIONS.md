# TrueIntent Known Limitations

Stated explicitly per `PROJECT_SPEC.md` §12 — credibility over overselling. Part A carries over the
spec's four items; Part B records issues **actually observed during implementation, training and
testing**; Part C records spec items deferred with no implementation.

Nothing in this document is a design intention — every claim below is a property of the code as
it stands on this branch.

## Part A — From the spec (§12, still true)

1. **No passive WhatsApp/Telegram scanning (E2E encryption).** The system is evidence-submission
   based (paste text, upload screenshot, paste link) by design and necessity — it cannot see
   inside encrypted chats.
2. **No live voice/deepfake detection.** Out of scope; future work only. A live scammer call is
   represented by a manual flag or an optional Android cellular call-state report. Neither
   detects scam content or caller intent.
3. **Behavioural text coverage is inadequate.** Module C trains on real text, but the fear/authority
   class rests on five short cited news excerpts, and every additional scam type rests on authored
   examples. Real-world recall is unvalidated.
4. **Calm coercion and paraphrases remain unvalidated.** Nothing here measures performance on
   well-scripted, low-urgency scam dialogue — the known false-negative mode.

## Part B — Discovered during implementation and testing

### B.1 — Module A is a benchmark, not a transfer-assessment model
Module A consumes exactly one feature: `amount`, in the original IEEE-CIS source unit. Time of
day, device novelty, call state and transfer count are absent because IEEE-CIS does not support
them for this purpose. No artifact is trained in this checkout, so there are **no** current Module A
metrics. Real INR transfer assessment is refused with an explicit 422, and the endpoint returns 503
rather than a substituted score when the artifact is missing. See
[Module A correctness](MODULE_A_CORRECTNESS.md).

### B.2 — Module B is a historical classifier; the rule weights and blend are unvalidated
- The typosquatting similarity cutoff (**0.78**) and every rule weight were chosen by judgment and
  never tuned. Classifier-only evaluation does not validate the weights or the 50/50 blend.
- Short brand tokens matched by substring (e.g. `sbi`) can collide with unrelated domains, and any
  `http://` URL takes a +0.20 penalty — so even `http://example.com/` is non-zero noise.
- Trained on the Kaggle *Web page phishing detection* v2 mirror of Hannousse & Yahiouche
  (Mendeley V3, DOI `10.17632/c2gw7fy2j4.3`, CC BY 4.0), collected **May 2020**. After
  deduplication, 11,427 rows: 9,141 train / 2,286 held out (seed 42).
- Classifier-only metrics: random split precision **0.9173**, recall **0.9020**, F1 **0.9096**,
  FPR **0.0814**; registered-domain-disjoint split precision **0.8624**, recall **0.9281**,
  F1 **0.8941**, FPR **0.1479**. These describe the classifier, **not** the blended score.
- 452 hostnames and 488 registered domains span both the random splits, and 142 near-duplicate path
  templates are shared. That is exactly why the domain-disjoint split is reported alongside it.
- A 2020 balanced benchmark is not a contemporary deployment distribution. Modern short links, IDN
  hosts and Indian banking/UPI campaign coverage are unverified and per-category recall is
  unmeasured.
- No PhishTank supplement: bulk downloads are documented, but the current terms now reference
  Cisco's terms and mark the older free-data permissions archived, so ML-training permission under
  the present terms is unclear. No feed was downloaded or blended in.
- An absent, unreadable or incompatible artifact falls back to rules with
  `ml_status: rules_only (…)`; `ml_status: active` is emitted only after successful classifier
  inference. The backend caches artifacts by (path, mtime, size), so restart after retraining.
- Full report: [Module B evaluation](MODULE_B_EVALUATION.md).

### B.3 — Module C's rare classes are thin, and most of the taxonomy is authored
The assembled intent set has **4,724 rows / 4,613 independent groups**: 4,507 public rows
(4,502 ham mapped to `benign`, weak-labelled corpus rows mapped to `other_fraud`), **5**
manually curated fear excerpts, and **117** authored/translated rows across nine scam types.
Label support is therefore 13 per authored class and 18 for `authority_fear`.
Five-fold grouped OOF macro F1 is **0.3264**; the binary scam-vs-benign view is far more flattering
(precision 0.8848, recall 0.9143, F1 0.8993) because it is dominated by the benign majority.
Hindi and Hinglish results are diagnostics on authored text, not real-language recall.
Keyword lists are retained for measured ablations only: the shipped artifact has
`retained_rules: []` and no rule overrides the score. No keyword-only path survives as a fallback —
a missing model makes the endpoint return 503 rather than a fake verdict. See
[Module C datasheet](../data/MODULE_C_DATASHEET.md) and
[Module C evaluation](MODULE_C_INTENT_EVALUATION.md).

### B.4 — Module A cannot contribute to fusion, and its old demo numbers are gone
The old low-amount "blind spot" demonstration was an artifact of a six-feature model that no longer
exists. With a single amount feature, card-fraud domain shift and no coercion labels, transaction
detection is unvalidated in either direction. Transaction-bearing `/check-combined` requests are
refused rather than silently downgraded. See B.1.

### B.5 — Module D learns a synthetic policy, not fraud
Module D's serving model is an availability-aware logistic policy with channel interactions. Its
training data is **600 invented incident families / 2,400 masked rows** scored against a
hand-written label policy. On the 200 synthetic test scenarios the serving model scores
F1 **0.8251** for A+B+C and **0.6849** for B+C. There are no linked or adjudicated real incidents
anywhere in the pipeline, so these numbers must not be presented as real-world performance.
Missing channels are encoded as *absent*, not as zero risk; unknown call state is distinct from
"no call". Fixed weights (A 0.45 / B 0.25 / C 0.30, renormalized) are used **only** when the
artifact is missing, and the response says so. See
[Module D evaluation](MODULE_D_FUSION_EVALUATION.md).

### B.6 — No device-history or call-attestation mechanism exists
There is no runtime device familiarity lookup, no transaction history service, and no attested call
signal. `device_id` is a client-supplied string and `call_telemetry` is an unattested, freshness-
checked JSON object. Freshness and device-ID equality are input checks, not proof of origin; the
Android companion's client-side state can be forged. Nothing in the system treats these as risk
evidence, because the model cannot use them.

### B.7 — OCR paths are contract-tested, not engine-tested
No Tesseract binary exists in this environment, so real OCR accuracy — especially on Hindi/Hinglish
or low-contrast screenshots — is unmeasured, and the 20-character/3-word "enough text" heuristic is
unvalidated. The English-only default model additionally excludes a large part of the intended user
base. `TESSERACT_CMD` and `TESSERACT_LANG` can be set (see `.env.example`) but neither is exercised
by the suite.

### B.8 — Demo-grade hardening
No database (nothing is persisted — good for privacy, poor for audit and feedback), no auth, no
rate limiting, no request logging of bodies (the access log carries method, path, status, duration
and request ID only — never bodies, URLs with content, or headers), and no human-feedback loop
(spec §9's optional loop is unimplemented). CORS admits any localhost port by default with
credentials off; production must enumerate origins via `TRUEINTENT_CORS_ORIGINS`. The frontend has
14 SSR regression tests (`npm test`), not browser end-to-end tests.

## Part C — Spec items with no implementation (deferred, not hidden)

- **SQLite persistence** (spec §7): nothing is stored server-side at all.
- **React Testing Library suite** (spec §7): not used; the frontend suite runs real components
  through `react-dom/server` under `node --test`.
- **WHOIS / domain-age lookup** (implied by spec §10's "registered recently"): never implemented.
  Module B judges structure only, so a freshly registered lookalike and a compromised old domain
  score identically on that axis.
- **Security-header inspection** (spec §5): not implemented. Destination analysis was removed
  entirely; see ADR-004.
- **Live page / redirect-chain / login-form inspection** (spec §5): removed for SSRF safety.
  `inspect_live_page()` is a no-network stub that performs no I/O and contributes no score weight.
- **LIME fallback** (spec §5/§10): only heuristic fallbacks exist.
- **Real jointly labelled incident evaluation, calm-message false-negative study, and a calibrated
  deployment evaluation**: not completed. Synthetic policy evaluation does not fill this gap.

## Android companion scope

Activity-only course demo, not a hardened telemetry pipeline. No background/foreground service,
overlay detection, AccessibilityService, MediaProjection, attestation or mTLS. READ_PHONE_STATE
observes cellular state on the default subscription, not arbitrary VoIP apps. The app submits the
IEEE-CIS source-unit benchmark contract, which the API may refuse with 503 when no artifact is
trained. See [scope and validation](ANDROID_COMPANION.md).