/**
 * Live-backend smoke check for the mobile client (run manually, not in CI).
 *
 * Usage from mobile/:
 *   EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 node scripts/check-backend.mjs
 *
 * Verifies: /health answers, /openapi.json exposes both mobile operations,
 * and POST /api/v1/analyze returns the documented mobile verdict shape.
 */
const base = (
  process.env['EXPO_PUBLIC_API_BASE_URL'] ??
  process.env['EXPO_PUBLIC_TRUEINTENT_API_URL'] ??
  'http://127.0.0.1:8000'
).replace(/\/+$/, '');

let failures = 0;
function check(name, ok, extra = '') {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra !== '' ? ` — ${extra}` : ''}`);
  if (!ok) failures += 1;
}

const health = await fetch(`${base}/health`);
check('GET /health answers', health.ok, `HTTP ${health.status}`);

const openapi = await (await fetch(`${base}/openapi.json`)).json();
const paths = Object.keys(openapi.paths ?? {});
check('POST /api/v1/analyze is documented', paths.includes('/api/v1/analyze'));
check(
  'POST /api/v1/analyze/screenshot is documented',
  paths.includes('/api/v1/analyze/screenshot'),
);

const verdict = await fetch(`${base}/api/v1/analyze`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://www.google.com/',
    message: 'Hey, are we still meeting for lunch tomorrow?',
  }),
});
const body = await verdict.json();
const data = body.data ?? {};
const required = [
  'risk_level',
  'score',
  'summary',
  'evidence',
  'url_findings',
  'message_findings',
  'unavailable_modules',
  'limitations',
  'recommended_action',
];
check('POST /api/v1/analyze answers', verdict.ok, `HTTP ${verdict.status}`);
for (const key of required) {
  check(`verdict carries ${key}`, data[key] !== undefined && data[key] !== null);
}
check('benign pair is not alarming', ['Low', 'Medium'].includes(data.risk_level));

if (failures > 0) {
  console.error(`\n${failures} check(s) failed against ${base}`);
  process.exit(1);
}
console.log(`\nAll mobile backend checks passed against ${base}`);
