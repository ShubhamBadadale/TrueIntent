# TrueIntent mobile client (React Native + Expo + TypeScript)

Working client for the TrueIntent FastAPI backend. All analysis runs
server-side (Modules B/C/D); the app renders verdicts and never contains ML
logic. Contract: `POST /api/v1/analyze` + `POST /api/v1/analyze/screenshot`,
documented in `../docs/MOBILE_API.md` and at `/docs` on a running backend.

## Layout

```
mobile/
  App.tsx                 entry + state-based navigation (no router dependency)
  app/                    screens: Splash, Home, Url/Message/Screenshot/Combined
                          scanners, reusable ResultScreen, About
  components/             ScreenContainer, ui (cards/buttons/loading/error/offline),
                          result (badge, score bar, evidence, modules, checklist)
  services/api.ts         the one centralized API client (fetch lives only here)
  hooks/                  useBackendHealth (non-blocking splash probe), useAnalyze
  types/api.ts            backend-matching interfaces + runtime guards
  constants/              config (env-driven base URL/timeouts), theme
  utils/                  risk + errors (pure, unit-tested) and image picking
  __tests__/              node:test unit tests over utils/types
  scripts/check-backend.mjs  live-backend smoke check (manual)
  scripts/integration-live.mjs  full matrix vs live backend + stub failure paths
  scripts/integration-model-down.mjs  degraded-model (no module_c) pass
  scripts/make-fixtures.py  generates binary upload fixtures (gitignored)
```

## Prerequisites

- Node 20+ and the backend running locally (`../run-backend.ps1` or `python -m backend`).
- Expo Go on a physical device, or an Android emulator / iOS simulator.

## Configure the backend URL

The app reads `EXPO_PUBLIC_API_BASE_URL` (see `constants/config.ts`;
`EXPO_PUBLIC_TRUEINTENT_API_URL` still works as a legacy alias).
Nothing else in the codebase names a host — switching environments is a
rebuild with a new value, never a source-code edit.

| Client | Value |
|---|---|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator / web | `http://127.0.0.1:8000` |
| Physical device (Expo Go) | `http://<your-lan-ip>:8000` (backend must bind a LAN address) |
| Deployed backend | `https://api.example.com` (or your host) |

```powershell
$env:EXPO_PUBLIC_API_BASE_URL = "http://10.0.2.2:8000"
npm install
npx expo start
```

Scan the QR code with Expo Go. The Home footer and the About screen always show
the active backend URL.

### Development networking notes

- **Android emulator:** the emulator is a virtual machine with its own
  loopback. `http://10.0.2.2` is the emulator's alias for your PC's
  `localhost`; `http://127.0.0.1:8000` inside the emulator would reach the
  emulator itself, not your backend.
- **Expo Go on a physical phone:** `localhost` / `127.0.0.1` on the phone
  refers to the phone itself — never your development PC. The phone and the
  PC must be on the same Wi-Fi, the backend must listen on a LAN interface
  (e.g. `python -m backend --host 0.0.0.0 --port 8000`, or set
  `TRUEINTENT_HOST=0.0.0.0`; see `run-backend.ps1`), and any host firewall
  must allow the port. Then use `http://<pc-lan-ip>:8000` (find it with
  `ipconfig`).
- **Deployed backend:** use the public `https://` URL. No client change beyond
  the env value; certificate errors surface as `offline` with a retry prompt.

## Scripts

| Command | What it proves |
|---|---|
| `npm run typecheck` | `tsc --noEmit` over the whole app |
| `npm run test:unit` | compiles `utils/` + `__tests__/` and runs `node --test` (offline) |
| `npm test` | typecheck + unit tests |
| `node scripts/check-backend.mjs` | live backend answers `/health`, documents both mobile operations, and returns the verdict shape (needs the server running) |
| `node scripts/integration-live.mjs` | full integration pass through the real compiled client: URL/message/combined, invalid/empty/oversized inputs, multipart screenshot matrix, stub-server failure paths (503s, corrupt bodies, 500s, timeout, offline) |
| `node scripts/integration-model-down.mjs` | degraded-model pass against a backend started without `module_c.pkl`: real 503s, URL-only still works |

## Screens

Splash (branding + non-blocking backend probe) → Home (Analyze Link / Message /
Screenshot / Combined + honesty disclaimer + backend status) → per-scanner input
with loading / retry / offline states → reusable Result screen (level badge,
summary, score, per-channel findings with ML-vs-heuristics split, evidence
cards, contributing vs **not-analyzed** modules, actions, expandable technical
details) → About (capabilities, limits, Module A benchmark status, privacy).

Design: cybersecurity theme (`constants/theme.ts`), automatic dark/light via
`useColorScheme`, safe areas, keyboard avoidance, scrolling everywhere, no
heavy animation.
