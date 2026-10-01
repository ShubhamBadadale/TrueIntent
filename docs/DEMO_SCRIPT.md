# TrueIntent — 5-Minute Live Demo Script

Every input and output below was re-measured against the current build (see
`docs/AUDIT_REPORT.md`). UI path and API path are interchangeable — the portal calls these exact
endpoints, proven by
`tests/test_integration.py::test_frontend_api_client_matches_backend_routes`.
If the UI stalls, run the `curl` fallback for that step and keep going.

## 0:00 — Setup (do before the audience arrives)

```bash
# Terminal 1 — backend (http://localhost:8000, docs at /docs)
.\run-backend.ps1            # or:  docker compose up --build
# Terminal 2 — frontend (http://localhost:5173)
.\run-frontend.ps1
```

Pre-flight (must return `{"status":"ok"}`):

```bash
curl http://localhost:8000/health
```

Check `ml_status` early: Module B and Module C report `active` only when a trained artifact loaded.
If Module C reports `503`, the text steps below will not work — see the recovery table.

Say (30s): *"Banks verify **who** you are. Nobody verifies **why** you're sending the money.
TrueIntent combines the message, the screenshot and the link you were given — and explains itself
in plain words. One risk index, and it tells you what it could not see."*

## 0:30 — (a) A clean submission scores Low

UI: **Combined Fraud Analysis** tab → URL `https://www.google.com/`, message
`Hey, are we still meeting for lunch tomorrow?` → *Analyze combined evidence*.

Fallback:

```bash
curl -X POST http://localhost:8000/check-combined -H "Content-Type: application/json" \
  -d '{"url":"https://www.google.com/","text":"Hey, are we still meeting for lunch tomorrow?"}'
```

Expect: tier **Low**, score **0.0938**. Say: *"Nothing alarming in either channel — and the
explanation still names what it skipped, so you can see what it did not check."*

## 1:30 — (b) A suspicious URL gets flagged, structurally

UI: **Check a Link** tab → paste `http://192.168.1.1/verify-account` → *Check this link*.
Fallback: `POST /check-url` with `{"url":"http://192.168.1.1/verify-account"}`.

Expect: score **0.7944** (79/100) with reasons *"Insecure protocol…"* and *"Host is a raw IP
address (192.168.1.1)…"*. Compare with `https://www.google.com/search?q=test` → **0.0357** with no
reasons. Say: *"No domain name, no encryption. Those are structural tells you can check yourself."*

## 2:30 — (c) A scam message is flagged and its tactic is named

UI: **Check a Message** tab → paste
`You are under investigation for money laundering. Stay on the line and do not disconnect.`
Fallback: `POST /check-message` (form field `text`) with the same string.

Expect: score **0.707**, signature **`fear_authority`**, intent **`digital_arrest`**, and reasons
that name the prediction and its limitation rather than asserting fraud. Say: *"This is the
digital-arrest script. The system names the tactic — fear/authority — and is explicit that this is
a prediction, not a verified finding."*

## 3:30 — (d) THE THESIS MOMENT: combined evidence escalates ★

Say: *"Now the point of the whole project. Neither channel was conclusive on its own — a link and a
message. Watch what happens when the tool weighs them together instead of checking them in
isolation."*

Combined tab: URL `http://192.168.1.1/verify-account`, message
`You are under investigation. Update your KYC here: http://192.168.1.1/verify-account immediately.`,
call status **Yes**.

Fallback:

```bash
curl -X POST http://localhost:8000/check-combined -H "Content-Type: application/json" \
  -d '{"url":"http://192.168.1.1/verify-account","text":"You are under investigation. Update your KYC here: http://192.168.1.1/verify-account immediately.","active_call":true}'
```

Expect — tier **High**, score **0.5086**:

> *High synthetic-policy risk index (0.51). Factors: link risk score 0.79; message text risk score
> 0.68. Modules contributing: Module B, Module C. Modules skipped: Module A (no transaction
> submitted). This index is not a calibrated real-world fraud probability.*

Say: *"Same evidence, one channel at a time versus together — and it tells you which channels spoke
and which stayed silent. That correlation layer **is** the project. Notice what it will not do: it
will not give a transfer risk number, because we have no data that could support one."*

## 4:15 — (e) Say no out loud: the transaction benchmark

UI: **Transaction Benchmark** tab → amount `500`.

Expect: the UI labels the result a benchmark and refuses transfer-risk tiers. If no artifact is
trained the API returns **503**: *"Module A benchmark artifact is missing."*

Say: *"This is the honesty part of the project. We cannot score your transfer, so we refuse to guess.
A tool that invents a number here would be more dangerous than no tool at all."*

## 4:45 — Close (30s)

*"Rules and classifiers where real data exists, explicit unavailability where it does not — check
`ml_status` and the explanation text. Limitations are on the table in `docs/LIMITATIONS.md`.
Thank you — happy to take questions, or the screenshot upload path live."*

## If something fails (recovery lines)

| Failure | Line |
|---|---|
| Backend down (`health` fails) | *"The API isn't up — one moment."* Restart Terminal 1, re-run `curl …/health`. |
| Frontend blank | *"The API carries the demo."* Use the `curl` fallback for the current step. |
| `/check-message` or `/check-combined` returns 503 | *"The message model isn't trained in this build."* Retrain with `.\.venv\Scripts\python.exe ml\train_module_c.py`, or move to step (b), which is rules-plus-classifier only. |
| `/check-transaction` returns 503 or 422 | Expected: Module A needs authorized IEEE-CIS data. *"That's deliberate — see step (e)."* |
| Screenshot upload path | *"OCR needs the Tesseract binary; paste the text instead — same pipeline."* |
| Scores differ slightly | *"Deterministic on the committed seed — retraining reproduces it. Scores, not vibes."* |