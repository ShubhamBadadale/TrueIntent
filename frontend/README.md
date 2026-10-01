# TrueIntent web portal (Module E)

React + Vite + Tailwind front end for the TrueIntent FastAPI backend. It renders
four views: **Combined Fraud Analysis** (default), **Check a Link**,
**Check a Message / Screenshot**, and the **Transaction Benchmark**.

## Commands

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production bundle into dist/
npm run preview    # serve the built bundle
npm run lint       # oxlint
npm test           # node --test tests/*.test.mjs
```

`npm test` boots a real Vite SSR server, loads the actual modules and renders
the real components with `react-dom/server` against a mocked `fetch`. It is not a
browser end-to-end suite; there is no headless-browser dependency in this
project.

## Backend URL

The API client in `src/api.js` reads `VITE_API_URL` and defaults to
`http://localhost:8000`. To point the portal elsewhere:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

In Docker Compose the same variable is supplied as a build argument, so the
bundle must be rebuilt (`docker compose build frontend`) to change it.

## Limits mirrored from the backend

`src/api.js` exports the same caps the API enforces so oversized input fails
locally with a readable message instead of a bare 422: 20,000 characters of
text, 8,192 characters of URL, 10 MB per screenshot, and PNG/JPEG/WebP/BMP only.

## Honest-unavailable behaviour

Unavailable evidence is rendered as such. Transaction risk is always shown as
"Unavailable — not scored" because Module A is a source-unit research benchmark
and is deliberately excluded from combined fusion. Risk Index values are
uncalibrated and are labelled as such in every results view.