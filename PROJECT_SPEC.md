# TrueIntent — Multi-Channel Fraud Intent Verification System

*(Working title — rename freely; referred to as "TrueIntent" throughout this doc)*

## Tagline
Banks verify *who* you are. Nobody verifies *why* you're sending the money. TrueIntent closes that gap.

---

## 1. Problem Statement

Modern authentication (OTP, biometrics, hardware tokens) verifies **identity**, not **intent**. A legitimate,
verified user can be psychologically coerced into authorizing a fraudulent transaction from their own trusted
device — this is Authorised Push Payment (APP) fraud, and it powers scams like "Digital Arrest" impersonation
and fake stock-trading schemes.

**Why this is a real, current problem (not a manufactured one):**
- India reported ₹22,495 Crore in citizen-facing cyber fraud losses in 2025 (I4C data), while RBI-reported
  *bank-side* digital payment fraud was only ₹29 Crore in the same period. This gap is the core evidence for
  the project: the fraud isn't a technical breach, it's a psychologically authorized transfer that looks
  legitimate to the bank.
- Over 50% of scams targeting Indian users now originate from organized scam compounds (Cambodia, Myanmar,
  Laos), delivered via WhatsApp/Telegram — channels that are end-to-end encrypted and cannot be passively
  scanned by any tool, including this one.
- TRAI's March 2026 mandate forces telecom-layer AI blocking of spam calls and SMS — but this cannot reach
  encrypted messaging apps, which is where the volume has already migrated. This is the enforcement gap
  TrueIntent is scoped to sit in: **user-submitted evidence**, not passive network scanning.

**Refined problem statement:**
Design a system that helps a user or analyst verify whether they are being manipulated into an authorized
but fraudulent transaction — by correlating real-time transaction context (e.g. an active phone call during
a transfer) with user-submitted evidence (chat screenshots, suspicious links, call details) — and explains
*why* something looks risky in plain language, rather than issuing a silent yes/no.

---

## 2. Target Users

Two primary personas, because the data shows they're targeted by *different* scam types with *different*
psychological levers — this matters for how the system should talk to each of them:

| Persona | Primary Threat | Manipulation Lever | Design Implication |
|---|---|---|---|
| **Senior citizens / retirees** | "Digital Arrest," authority impersonation (fake police/govt video calls) | Fear, urgency, authority | Interface must be simple, calm, non-technical; explanation text should be plain-language, not jargon |
| **Working-age adults** | Fake stock trading / investment groups on WhatsApp-Telegram | Greed, FOMO, social proof | Needs to catch "too good to be true" return promises and group-based social engineering patterns |

Secondary user: a **human analyst/reviewer** who needs the explainability layer (SHAP) to understand *why*
a case was flagged, not just a score.

---

## 3. Core Idea (one-liner)

**Correlate transaction context + user-submitted evidence into one explainable risk score, instead of
checking each signal (call, message, link) in isolation.**

The individual detectors (URL checker, message/screenshot analyzer, call-state correlation) are not
individually novel — each exists in prior work. The contribution is the **unified, explainable
correlation layer** across them, motivated directly by the fact that real scams chain multiple channels
(e.g. WhatsApp message → fake investment link → phone call demanding urgency).

---

## 4. Scope — Core (buildable, demonstrable) vs Future (mention only)

| Core (build this) | Future / Out of Scope (mention in report only) |
|---|---|
| Transaction + active-call-state correlation risk engine (XGBoost) | Live passive scanning of WhatsApp/Telegram (impossible — E2E encrypted) |
| User-submitted screenshot/chat analyzer (OCR + NLP scam-pattern detection) | Real-time voice deepfake detection (needs ASVspoof-scale audio pipeline) |
| URL/link safety checker (feeds into message analyzer) | Multilingual, accent-robust production voice models |
| SHAP-based plain-language explanation layer | Federated learning across banks/orgs |
| Unified risk score (Low/Medium/High/Critical) | Enterprise-grade deployment / browser extension |
| Simple web portal (paste link / upload screenshot / simulate transaction+call scenario) | Automated legal takedown / law-enforcement integration |

---

## 5. Features / Modules

**Module A — Transaction–Call Correlation Engine (core differentiator)**
- Input: transaction amount, time, device signals, `is_active_call` flag, transaction velocity (features
  already scoped in prior team work)
- Model: XGBoost classifier → risk probability
- Output feeds into unified scorer

**Module B — Link/URL Safety Checker**
- Input: a pasted URL
- Checks: URL structure (length, special chars, IP-based links, typosquatting against known brands),
  redirect chain, presence of login forms, basic security headers
- Output: safe / suspicious / dangerous + reason

**Module C — Message/Screenshot Scam Analyzer**
- Input: pasted text or an uploaded screenshot (OCR extracts text first)
- Checks for scam-language patterns — split into **two behavioral signatures**, not one generic model:
  - *Fear/authority signature* (digital arrest style: "you are under investigation," "stay on the call")
  - *Greed/opportunity signature* (fake trading style: guaranteed returns, urgency to invest now)
- Any links found in the text are automatically passed to Module B
- Output: risk score + which signature it matched + explanation

**Module D — Unified Risk Scoring & Explanation Layer**
- Combines Module A + B + C signals into one score (Low/Medium/High/Critical)
- SHAP (or LIME as fallback) generates a plain-language explanation: "flagged because: active call during
  transfer + message contains urgency + investment-return language"
- This module is the actual thesis of the project — do not let it become an afterthought

**Module E — Simple Portal (UI)**
- Three input surfaces: "Check a link," "Check a message/screenshot," "Simulate a transaction scenario"
- One shared results view showing the unified score + explanation, in plain language

---

## 6. System Architecture

```
                        ┌─────────────────────────┐
                        │      Frontend (UI)       │
                        │  React — 3 input forms   │
                        └────────────┬─────────────┘
                                     │ REST calls
                        ┌────────────▼─────────────┐
                        │     API Layer (FastAPI)   │
                        └──┬───────┬───────┬────────┘
                           │       │       │
              ┌────────────▼┐ ┌────▼────┐ ┌▼─────────────┐
              │ Module B     │ │ Module C │ │ Module A     │
              │ URL Checker  │ │ Msg/OCR  │ │ Txn+Call     │
              │ (rules + ML) │ │ Analyzer │ │ Correlation  │
              │              │ │ (OCR+NLP)│ │ (XGBoost)    │
              └────────────┬─┘ └────┬─────┘ └┬─────────────┘
                           │        │         │
                           └───┬────┴────┬────┘
                                ▼         ▼
                        ┌──────────────────────┐
                        │   Module D — Unified   │
                        │   Risk Scorer + SHAP   │
                        │   Explanation Engine   │
                        └───────────┬────────────┘
                                    ▼
                        ┌──────────────────────┐
                        │  Response: score +    │
                        │  plain-language why   │
                        └──────────────────────┘
```

Storage: only anonymized features persisted (no raw screenshots, no raw transaction PII stored long-term) —
consistent with the privacy-by-design principle from the earlier AI-Sentinel spec.

---

## 7. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| ML — tabular (Module A) | XGBoost | Fast, interpretable-enough, already scoped in prior work |
| ML — text (Module C) | scikit-learn baseline (TF-IDF + Logistic Regression) → optional transformer upgrade | Keep MVP simple, upgrade path exists |
| OCR (Module C) | Tesseract via `pytesseract` | Free, local, no external API dependency |
| Explainability | SHAP (`shap` library) | Directly matches prior OmniGuard spec, produces per-feature contribution |
| Backend | FastAPI | Lightweight, async, easy to demo |
| Frontend | React (+ Tailwind) | Fast to build, matches skillset |
| Database | SQLite (course project scale) | No need for Postgres at this scope |
| Testing | Pytest (backend), React Testing Library (frontend) | Standard, simple |
| Packaging | Docker (optional, for portability) | Makes it demoable on any machine |
| Version control | Git + GitHub | Standard |

---

## 8. Data Requirements

**Be upfront in the report: this is the hardest part of the project, not the modeling.**

| Module | Data needed | Where it comes from |
|---|---|---|
| Module A (txn+call) | Tabular transaction dataset with amount, time, device signal, call-state flag | **Ask the user (you) to provide** — if unavailable, generate a realistic synthetic dataset with documented assumptions (state this clearly in the report as a limitation) |
| Module B (URL) | Labeled phishing vs. legitimate URL dataset | Public datasets exist (e.g. PhishTank, UCI Phishing Websites dataset) — confirm availability with the user before assuming |
| Module C (messages) | Labeled scam vs. legitimate message/chat text | Likely needs to be **manually curated/synthesized** (real scam transcripts are hard to source) — flag this as a scope decision, ask the user how much manual labeling effort is feasible |

**Build instruction for any coding agent implementing this:** whenever a dataset is required and not already
present in the repo, **stop and explicitly ask the user to provide it or approve a synthetic substitute** —
do not silently fabricate data as if it were real.

---

## 9. Methodology (pipeline, end to end)

```
INPUT (link / message+screenshot / transaction+call context)
   → PREPROCESSING (OCR if screenshot, feature extraction if transaction)
   → MODULE-LEVEL DETECTION (rules + ML per module)
   → MODULE-LEVEL RISK SCORE
   → UNIFIED WEIGHTED SCORING (Module D)
   → SHAP EXPLANATION GENERATION
   → OUTPUT: risk tier + plain-language reason
   → (optional) HUMAN FEEDBACK LOOP to correct false positives over time
```

---

## 10. Risk Scoring & Explainability

- Each module outputs an independent confidence/risk score (0–1).
- Module D combines them with a simple weighted sum (documented, tunable weights — not a black box) into
  a final tier: **Low / Medium / High / Critical**.
- SHAP values are computed per module's ML component and translated into a short natural-language sentence
  template, e.g.: *"Flagged as High risk because: (1) an active call was detected during the transfer,
  (2) the message contains urgency and authority-impersonation language, (3) the linked URL was registered
  recently and mimics a known bank domain."*

---

## 11. Evaluation Metrics

- Precision, Recall, F1-score, False-Positive Rate — per module and for the unified score.
- Explicitly report **false-negative behavior on subtle/calm-toned scam messages** (per earlier research:
  not all scam scripts sound urgent) — do not oversell accuracy here; this is a known, honest limitation.
- Ablation: show the unified score's performance vs. each module in isolation, to actually demonstrate the
  correlation-layer thesis with numbers, not just narrative.

---

## 12. Known Limitations (state these explicitly in the report — it builds credibility, not weakness)

1. Cannot passively scan WhatsApp/Telegram (E2E encryption) — system is evidence-submission based, not
   surveillance-based, by design and by necessity.
2. No live voice/deepfake detection in core scope — mentioned only as future work.
3. Message/screenshot dataset will likely be small and partially synthetic — label this clearly.
4. Rule-based/keyword components will under-perform on calm, well-scripted scam dialogue — flagged as an
   open research gap, not hidden.

---

## 13. Deliverables

- Working prototype (all 5 modules integrated, running locally or in Docker)
- GitHub repository with clean commit history, README, and setup instructions
- Test suite with meaningful coverage on Modules A–D
- Final report covering: problem statement, related work, methodology, architecture, results (with the
  metrics above), limitations, and future scope
- Demo script / walkthrough for evaluation day
