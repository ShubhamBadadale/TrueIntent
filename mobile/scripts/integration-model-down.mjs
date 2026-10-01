/**
 * Degraded-model integration pass: runs against a backend whose
 * ml/models/module_c.pkl has been temporarily moved aside (see the runner
 * notes in docs/MOBILE_API.md). Expects REAL 503s, never a fake verdict.
 *
 * Usage:
 *   EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 node scripts/integration-model-down.mjs
 */
import { pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoMobile = join(here, '..');
const BASE = (process.env['EXPO_PUBLIC_API_BASE_URL'] ?? 'http://127.0.0.1:8001').replace(/\/+$/, '');
process.env['EXPO_PUBLIC_API_BASE_URL'] = BASE;
const clientUrl = pathToFileURL(
  join(repoMobile, '.integration-dist', 'services', 'api.js'),
).href;
const client = await import(clientUrl);

let passed = 0;
let failed = 0;
function check(name, ok, extra = '') {
  if (ok) {
    passed += 1;
    console.log(`PASS  ${name}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${name}${extra !== '' ? ` — ${extra}` : ''}`);
  }
}
const isApiError = (e, code) =>
  e !== null && typeof e === 'object' && e.name === 'ApiError' && e.code === code;

console.log(`--- degraded backend (no module_c): ${BASE} ---`);

try {
  await client.analyzeMobile({ message: 'Your account will be suspended. Verify now.' });
  check('message without model is refused, never scored', false, 'no error thrown');
} catch (e) {
  check(
    'message without model is refused, never scored',
    isApiError(e, 'message_not_assessed') && e.status === 503,
    `code=${e?.code} status=${e?.status}`,
  );
}

try {
  const urlOnly = await client.analyzeMobile({ url: 'http://hdfcbaank-login.xyz/update-kyc' });
  check(
    'URL-only analysis still works while text model is down',
    ['High', 'Critical'].includes(urlOnly.risk_level)
      && urlOnly.url_findings !== null
      && urlOnly.unavailable_modules.includes('module_c'),
    `${urlOnly.risk_level}`,
  );
} catch (e) {
  check('URL-only analysis still works while text model is down', false, `code=${e?.code}`);
}

try {
  await client.analyzeMobile({
    url: 'http://hdfcbaank-login.xyz/update-kyc',
    message: 'Your account will be suspended. Verify now.',
  });
  check('combined degrades loudly instead of silently dropping text', false, 'no error thrown');
} catch (e) {
  check(
    'combined degrades loudly instead of silently dropping text',
    isApiError(e, 'message_not_assessed'),
    `code=${e?.code}`,
  );
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
