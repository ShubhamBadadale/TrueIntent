# How to Run This Project — TrueIntent

End-to-end instructions to set up, run, verify, and test TrueIntent.
Every command below was verified against this checkout on Windows 11
(PowerShell); Linux/macOS equivalents are given where they differ.

**What runs where (default ports)**

| Piece | Command | URL |
|---|---|---|
| Backend API (FastAPI) | `.\run-backend.ps1` | `http://localhost:8000` (docs at `/docs`) |
| Web portal (React + Vite) | `.\run-frontend.ps1` | `http://localhost:5173` |
| Mobile app (Expo) | `npx expo start` in `mobile/` | Expo Go QR / emulator |
| Docker demo | `docker compose up --build` | Same two URLs above |

---

## 1. Prerequisites

| Requirement | Version / notes | Check it |
|---|---|---|
| Python | 3.11+ (`py` launcher on Windows is fine) | `py --version` |
| Node.js | 20.19+ or 22.12+ | `node --version` |
| Git | any recent | `git --version` |
| Tesseract OCR binary | **Optional** — only for screenshot OCR. Text/URL flows work without it | `tesseract --version` |
| Expo Go app | **Optional** — only for running the mobile app on a physical phone | App store |

Install Tesseract only if you need screenshot analysis:

| OS | Command |
|---|---|
| Ubuntu / Debian | `sudo apt-get install -y tesseract-ocr` |
| macOS (Homebrew) | `brew install tesseract` |
| Windows (Winget) | `winget install UB-Mannheim.TesseractOCR` |

If Tesseract is installed but not on `PATH` (common on Windows), point to it
explicitly — see `.env.example` (`TESSERACT_CMD`). Without it, screenshot
endpoints answer `503 ocr_unavailable`; nothing else is affected.

---

## 2. One-time setup (fresh clone)

```powershell
git clone https://github.com/ShubhamBadadale/TrueIntent.git
cd TrueIntent
.\setup.ps1
```

Linux / macOS:

```bash
chmod +x setup.sh run-backend.sh run-frontend.sh
./setup.sh
```

What this does (see `setup.ps1`, `Makefile`):

1. Creates the repo-root virtualenv `.venv/` (the **only** Python env — there is no `backend/venv`).
2. Installs `backend/requirements.txt` + `backend/requirements-dev.txt` into it.
3. Runs `npm install` in `frontend/` (and separately in `mobile/` — see §5).

No configuration is needed: the app starts with safe defaults and no secrets.
Copy `.env.example` to `.env` only if you want to override limits, ports, CORS,
or log format.

---

## 3. Run the backend (required for everything)

```powershell
.\run-backend.ps1
```

This runs the single documented command from the repo root:

```powershell
.\.venv\Scripts\python.exe -m backend --port 8000
```

(Bash: `./run-backend.sh`, or `.venv/bin/python -m backend --port 8000`.)

**Verify it:**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health          # -> status: ok
Invoke-RestMethod http://127.0.0.1:8000/ready | Select-Object -ExpandProperty data
```

Expected `/ready` on a fresh checkout (verified):

```text
status: degraded (= True) — this is NORMAL, not a failure:
  module_a  unavailable  (no IEEE-CIS artifact in checkout; benchmark answers 503)
  module_b  ok           (URL classifier active)
  module_c  ok           (message model active)
  module_d  ok           (fusion policy active)
  ocr       unavailable  (no Tesseract binary; screenshot answers 503)
```

Interactive API docs: `http://localhost:8000/docs`.

**Try a real analysis** (verified output from this checkout):

```powershell
@{url="https://example.com/login"} | ConvertTo-Json |
  Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/analyze/url -Method Post `
    -ContentType "application/json" | Select-Object -ExpandProperty data
# score 0.5002, risk_index 50

@{message="Your account will be suspended. Share your OTP now to verify immediately."} |
  ConvertTo-Json |
  Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/analyze -Method Post `
    -ContentType "application/json" | Select-Object -ExpandProperty data `
  | Select-Object risk_level, score
# risk_level Medium, score ~0.48
```

Keep this terminal running — frontend, mobile, and tests all talk to it.

---

## 4. Run the web portal (Module E)

New terminal (backend must already be running):

```powershell
.\run-frontend.ps1
```

Open `http://localhost:5173`. The portal calls the backend at
`http://localhost:8000` by default; to target a different backend:

```powershell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev --prefix frontend
```

---

## 5. Run the mobile app (Expo + TypeScript)

Prerequisites: backend running (§3), `npm install` once inside `mobile/`.

```powershell
cd mobile
npm install
```

Point the app at your backend with **one** environment variable
(no source-code edits needed — see `mobile/constants/config.ts`):

| Client | Value |
|---|---|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator / web | `http://127.0.0.1:8000` |
| Physical phone (Expo Go) | `http://<your-lan-ip>:8000` — same Wi-Fi, backend bound to LAN (see below) |

```powershell
$env:EXPO_PUBLIC_API_BASE_URL = "http://10.0.2.2:8000"   # pick your row
npx expo start
```

Scan the QR code with Expo Go. (`EXPO_PUBLIC_TRUEINTENT_API_URL` still works
as a legacy alias.) The Home footer and About screen always display the active
backend URL, so you can confirm the app is pointed correctly.

> **Physical phone networking:** `localhost` on a phone means the phone
> itself, never your PC. Put both on the same Wi-Fi, start the backend bound
> to your LAN (`.\.venv\Scripts\python.exe -m backend --host 0.0.0.0 --port 8000`,
> allow the firewall port), find the PC's LAN IP with `ipconfig`, and use
> `http://<that-ip>:8000` as the env value.

Verify the mobile/backend contract without a phone:

```powershell
cd mobile
node scripts/check-backend.mjs        # health + openapi + verdict shape (needs backend)
```

---

## 6. Run the tests

Backend + ML suite (verified: **306 passed, 2 skipped** — the skips need
Tesseract plus user-supplied sample screenshots):

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Web portal regressions (verified: **14 passed**):

```powershell
cd frontend; npm test
```

Mobile checks (verified: typecheck clean, **13 unit tests passed**):

```powershell
cd mobile; npm test        # tsc --noEmit + node --test units
```

---

## 7. (Optional) Retrain the models

From the repo root. Module D trains from a clean checkout; B and C need their
CSV inputs first (see `data/README.md`); **Module A cannot be trained here**
(it needs authorized IEEE-CIS data and refuses to fabricate a substitute):

```powershell
.\.venv\Scripts\python.exe ml\train_module_b.py
.\.venv\Scripts\python.exe ml\train_module_c.py
.\.venv\Scripts\python.exe ml\train_module_d.py
```

Restart the backend afterwards to clear its in-memory model caches.

## 8. (Optional) Docker demo

```bash
docker compose up --build
# frontend http://localhost:5173 · backend http://localhost:8000
docker compose down -v   # stop
```

Compose mounts `ml/models` read-only — supply trusted artifacts built in the
pinned Python 3.11 environment. Container startup was not verified on this
machine (no Docker here); treat it as documented-but-unverified.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `/ready` shows `degraded: True` | Normal on a fresh checkout (no Module A artifact, no Tesseract). URL/message/combined analysis still work. |
| `No .venv found. Run .\setup.ps1 first.` | Run §2 setup; the venv must be `.venv/` at repo root. |
| `http://localhost:5173` won't load but Vite says ready | Vite binds IPv6 `[::1]` here; `localhost` works, literal `127.0.0.1` may not. Use `http://localhost:5173`. |
| Screenshot endpoints return `503 ocr_unavailable` | Install Tesseract (§1) or set `TESSERACT_CMD`. |
| Transaction benchmark returns `503` | Expected without the IEEE-CIS artifact; by design it never substitutes a score. |
| Expo app shows backend unreachable | Wrong base URL for the client type (see table in §5); confirm with `node scripts/check-backend.mjs` using the same URL. |
| Port already in use | Another `python -m backend` is running — stop it, or pass a different `--port` (and point clients at it). |
| ML test failures after retraining | Restart the backend (caches) and re-run that module's trainer. |

Key references: [`README.md`](README.md) (full product doc),
[`docs/MOBILE_API.md`](docs/MOBILE_API.md) (mobile contract + networking),
[`docs/API_V1.md`](docs/API_V1.md) (versioned API contract),
[`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) (5-minute demo),
[`mobile/README.md`](mobile/README.md) (client internals).
