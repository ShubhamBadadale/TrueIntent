/**
 * Full mobile<->backend integration pass.
 *
 * Drives the ACTUAL compiled TypeScript client (mobile/.integration-dist,
 * built from services/api.ts via tsconfig.integration.json) against a live
 * backend, plus raw multipart calls in the exact wire format React Native
 * FormData produces, plus a local stub server for failure paths that must
 * not mutate backend state (model-unavailable, abstention, corrupt bodies,
 * HTTP 500s, hangs).
 *
 * Usage (backend already running):
 *   EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 node scripts/integration-live.mjs
 */
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoMobile = join(here, '..');
// Windows ESM loader requires file:// URLs for absolute paths.
const clientUrl = pathToFileURL(
  join(repoMobile, '.integration-dist', 'services', 'api.js'),
).href;

const BASE = (process.env['EXPO_PUBLIC_API_BASE_URL'] ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');
process.env['EXPO_PUBLIC_API_BASE_URL'] = BASE;

const client = await import('../.integration-dist/services/api.js');

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
function isApiError(e, code) {
  return e !== null && typeof e === 'object' && e.name === 'ApiError' && e.code === code;
}

// ---------------------------------------------------------------- live backend
console.log(`--- live backend: ${BASE} ---`);

const health = await client.checkBackendHealth(5000);
check('health probe reachable', health.reachable === true, JSON.stringify(health));

const benignUrl = await client.analyzeMobile({ url: 'https://www.google.com/' });
check('URL analysis returns verdict shape',
  ['Low', 'Medium', 'High', 'Critical'].includes(benignUrl.risk_level)
  && typeof benignUrl.score === 'number'
  && typeof benignUrl.summary === 'string' && benignUrl.summary.length > 0
  && Array.isArray(benignUrl.safety_actions) && benignUrl.safety_actions.length > 0
  && benignUrl.url_findings !== null && benignUrl.message_findings === null
  && benignUrl.ocr_findings === null);
check('benign URL is not alarming', ['Low', 'Medium'].includes(benignUrl.risk_level),
  `${benignUrl.risk_level} score=${benignUrl.score}`);

const phish = await client.analyzeMobile({ url: 'http://hdfcbaank-login.xyz/update-kyc' });
check('phishing URL detected with indicators',
  ['High', 'Critical'].includes(phish.risk_level)
  && phish.url_findings !== null && phish.url_findings.reasons.length > 0,
  `${phish.risk_level} score=${phish.score}`);

const benignMsg = await client.analyzeMobile({ message: 'Hey, are we still meeting for lunch tomorrow?' });
check('message analysis returns ML + heuristic split',
  benignMsg.message_findings !== null
  && typeof benignMsg.message_findings.text_assessed === 'boolean'
  && Array.isArray(benignMsg.message_findings.heuristic_evidence)
  && benignMsg.url_findings === null,
  `assessed=${benignMsg.message_findings?.text_assessed}`);

const scamMsg = await client.analyzeMobile({
  message: 'Your account will be suspended. Share your OTP now to verify immediately.',
});
check('scammy message surfaces heuristic categories',
  scamMsg.message_findings !== null
  && scamMsg.message_findings.heuristic_evidence.length > 0
  && new Set(scamMsg.message_findings.heuristic_evidence.map((h) => h.category)).size >= 1,
  `cats=${[...new Set((scamMsg.message_findings?.heuristic_evidence ?? []).map((h) => h.category))].join(',')}`);

const combined = await client.analyzeMobile({
  url: 'http://hdfcbaank-login.xyz/update-kyc',
  message: 'Your account will be suspended. Verify now.',
});
check('combined URL+message names participating modules',
  combined.url_findings !== null && combined.message_findings !== null
  && combined.analyzed_modules.includes('module_b')
  && combined.analyzed_modules.includes('module_c')
  && Array.isArray(combined.unavailable_modules),
  `analyzed=${combined.analyzed_modules.join(',')} unavailable=${combined.unavailable_modules.join(',')}`);

try {
  await client.analyzeMobile({ url: 'not a url' });
  check('invalid URL rejected', false, 'no error thrown');
} catch (e) {
  check('invalid URL rejected', isApiError(e, 'invalid_url'), `code=${e?.code}`);
}

try {
  await client.analyzeMobile({ message: '   ' });
  check('empty message rejected', false, 'no error thrown');
} catch (e) {
  check('empty message rejected', e?.code === 'validation_error' || e?.code === 'missing_input',
    `code=${e?.code} status=${e?.status}`);
}

try {
  await client.analyzeMobile({ url: `https://example.com/${'x'.repeat(9000)}` });
  check('oversized URL rejected', false, 'no error thrown');
} catch (e) {
  check('oversized URL rejected', isApiError(e, 'invalid_url'), `code=${e?.code}`);
}

try {
  await client.analyzeMobile({ message: 'x'.repeat(21000) });
  check('overlong message rejected', false, 'no error thrown');
} catch (e) {
  check('overlong message rejected', isApiError(e, 'validation_error'), `code=${e?.code}`);
}

// ------------------------------------------------- multipart (wire-identical)
console.log('--- multipart screenshot (raw fetch, RN FormData wire format) ---');
const FIX = join(repoMobile, 'scripts', 'fixtures');
const pngBytes = readFileSync(join(FIX, 'valid.png'));
const bigBytes = readFileSync(join(FIX, 'oversized.bmp'));

async function postScreenshot(fields, file) {
  const form = new FormData();
  if (file !== null) {
    form.append('image', new Blob([file.bytes], { type: file.mime }), file.name);
  }
  for (const [k, v] of Object.entries(fields)) form.append(k, v);
  const res = await fetch(`${BASE}/api/v1/analyze/screenshot`, { method: 'POST', body: form });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* corrupt body case */ }
  return { status: res.status, json, text };
}

let r = await postScreenshot({}, { bytes: pngBytes, mime: 'image/png', name: 'chat.png' });
check('screenshot reaches OCR stage (503 ocr_unavailable, no tesseract here)',
  r.status === 503 && r.json?.success === false && r.json?.error?.code === 'ocr_unavailable'
  && typeof r.json?.error?.message === 'string' && r.json.error.message.length > 0
  && typeof r.json?.meta?.request_id === 'string',
  `HTTP ${r.status} code=${r.json?.error?.code}`);

r = await postScreenshot({}, { bytes: Buffer.from('this is not an image at all'), mime: 'image/png', name: 'chat.png' });
check('garbage bytes refused as unreadable_image',
  r.status === 400 && r.json?.error?.code === 'unreadable_image', `HTTP ${r.status}`);

r = await postScreenshot({}, { bytes: pngBytes, mime: 'text/plain', name: 'chat.txt' });
check('undeclared type refused as unsupported_media_type',
  r.status === 415 && r.json?.error?.code === 'unsupported_media_type', `HTTP ${r.status}`);

r = await postScreenshot({}, { bytes: bigBytes, mime: 'image/bmp', name: 'big.bmp' });
check('oversized image refused as payload_too_large',
  r.status === 413 && r.json?.error?.code === 'payload_too_large', `HTTP ${r.status}`);

r = await postScreenshot({ url: 'https://www.google.com/' }, null);
check('screenshot endpoint without file still analyzes URL',
  r.status === 200 && r.json?.success === true
  && r.json?.data?.url_findings !== null && r.json?.data?.ocr_findings === null,
  `HTTP ${r.status}`);

// ------------------------------------------------------- stub-server handling
console.log('--- stub server: failure-path handling in the real client ---');
function startStub(handler) {
  const server = http.createServer(handler);
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}
const stubAddress = (server) => `http://127.0.0.1:${server.address().port}`;
function errorEnvelope(code, module) {
  return {
    success: false,
    error: { code, message: `stubbed ${code}`, module, details: {} },
    meta: { request_id: 'stub-123', api_version: 'v1' },
  };
}

// NOTE: the client bakes API_BASE_URL at import time, so each stub case runs
// in a fresh child process with EXPO_PUBLIC_API_BASE_URL pointed at the stub.
async function runAgainstStub(stubHandler, snippet) {
  const server = await startStub(stubHandler);
  const url = stubAddress(server);
  const runner = `process.env.EXPO_PUBLIC_API_BASE_URL=${JSON.stringify(url)};
const client = await import(${JSON.stringify(clientUrl)});
${snippet}`;
  const { execFile } = await import('node:child_process');
  const out = await new Promise((resolve) => {
    execFile(process.execPath, ['--input-type=module', '-e', runner], (err, stdout, stderr) => {
      resolve({ err, stdout: String(stdout), stderr: String(stderr) });
    });
  });
  server.close();
  return out;
}

let out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(errorEnvelope('model_unavailable', 'module_c')));
  },
  `try { await client.analyzeMobile({ message: 'hello' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code + ' module=' + e.module + ' rid=' + e.requestId); }`,
);
check('model-unavailable 503 surfaces code/module/requestId',
  out.stdout.includes('RESULT code=model_unavailable module=module_c rid=stub-123'), out.stdout.trim());

out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(errorEnvelope('message_not_assessed', 'module_c')));
  },
  `const h = await client.checkBackendHealth(2000);
   try { await client.analyzeMobile({ message: 'hello' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code + ' health=' + h.reachable); }`,
);
check('abstention 503 surfaces message_not_assessed (never a fake verdict)',
  out.stdout.includes('RESULT code=message_not_assessed'), out.stdout.trim());

out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end('this is not json{{{');
  },
  `try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code + ' name=' + e.name); }`,
);
check('corrupt (non-JSON) body becomes internal_error, no crash',
  out.stdout.includes('RESULT code=internal_error name=ApiError'), out.stdout.trim());

out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ hello: 'world' }));
  },
  `try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code); }`,
);
check('non-envelope JSON becomes internal_error', out.stdout.includes('RESULT code=internal_error'),
  out.stdout.trim());

out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: false, meta: { request_id: 'x', api_version: 'v1' } }));
  },
  `try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code); }`,
);
check('success:false without error body becomes internal_error',
  out.stdout.includes('RESULT code=internal_error'), out.stdout.trim());

out = await runAgainstStub(
  (_req, res) => {
    res.writeHead(500, { 'Content-Type': 'text/html' });
    res.end('<html><body>proxy explosion</body></html>');
  },
  `try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code + ' status=' + e.status); }`,
);
check('HTTP 500 HTML body becomes internal_error with status',
  out.stdout.includes('RESULT code=internal_error status=500'), out.stdout.trim());

console.log('--- timeout (hanging stub, ~30s client budget) ---');
out = await runAgainstStub(
  (_req, _res) => { /* never respond */ },
  `try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
   catch (e) { console.log('RESULT code=' + e.code); }`,
);
check('hung server maps to timeout ApiError', out.stdout.includes('RESULT code=timeout'),
  out.stdout.trim().slice(0, 120));

console.log('--- backend unavailable (closed port) ---');
{
  const { execFile } = await import('node:child_process');
  const code = `process.env.EXPO_PUBLIC_API_BASE_URL='http://127.0.0.1:9';
const client = await import(${JSON.stringify(clientUrl)});
const h = await client.checkBackendHealth(2000);
console.log('HEALTH reachable=' + h.reachable);
try { await client.analyzeMobile({ url: 'https://example.com/' }); console.log('RESULT no-throw'); }
catch (e) { console.log('RESULT code=' + e.code); }`;
  const res = await new Promise((resolve) => {
    execFile(process.execPath, ['--input-type=module', '-e', code], (err, stdout, stderr) => {
      resolve({ stdout: String(stdout), stderr: String(stderr) });
    });
  });
  check('health probe reports unreachable, no throw', res.stdout.includes('HEALTH reachable=false'),
    res.stdout.trim());
  check('refused connection maps to offline ApiError', res.stdout.includes('RESULT code=offline'),
    res.stdout.trim());
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
