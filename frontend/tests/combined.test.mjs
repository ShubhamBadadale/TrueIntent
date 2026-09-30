import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

let server, workflow, Results
before(async () => {
  server = await createServer({ server: { middlewareMode: true, watch: null, ws: false }, appType: 'custom' })
  workflow = await server.ssrLoadModule('/src/combinedAnalysis.js')
  Results = (await server.ssrLoadModule('/src/components/CombinedResults.jsx')).default
})
after(async () => { await server?.close() })

const response = { tier: 'High', score: .6, explanation: 'Suspicious evidence.', modules: {
  module_b: { score: .6, reasons: ['Suspicious domain'], ml_status: 'rules_only' },
  module_c: { score: .7, reasons: ['Pressure to act'], ml_status: 'active' },
}, details: { scoring_method: 'fixed_weights_missing_model' } }
const imageFile = () => new File(['image fixture'], 'chat.png', { type: 'image/png' })

test('Combined Fraud Analysis is the default; individual tabs remain', async () => {
  const App = (await server.ssrLoadModule('/src/App.jsx')).default
  const html = renderToStaticMarkup(createElement(App))
  for (const text of ['Combined Fraud Analysis', 'Check a Link', 'Check a Message', 'Transaction Benchmark', 'Analyze combined evidence']) assert.ok(html.includes(text))
  for (const field of ['combined-text', 'combined-image', 'combined-url', 'combined-amount', 'combined-when', 'combined-velocity', 'combined-call']) assert.ok(html.includes(field))
})

test('optional inputs validate without treating empty amounts as zero', () => {
  assert.throws(() => workflow.prepareCombinedInput(workflow.EMPTY_INPUT), /Add a message/)
  assert.deepEqual(workflow.prepareCombinedInput({ text: '  hello  ' }), { text: 'hello', url: undefined, context: {} })
  for (const amount of ['-1', '0', 'Infinity', 'abc']) assert.throws(() => workflow.prepareCombinedInput({ amount }), /Amount/)
  for (const velocity of ['-1', '1.5']) assert.throws(() => workflow.prepareCombinedInput({ velocity }), /Transfers/)
  for (const url of ['javascript:alert(1)', 'ftp://example.com', 'not a url', 'http://[bad']) assert.throws(() => workflow.prepareCombinedInput({ url }), /valid HTTP/)
  assert.throws(() => workflow.prepareCombinedInput({ text: 'hello' }, { type: 'image/png', size: 10 * 1024 * 1024 + 1 }), /10 MB/)
  assert.throws(() => workflow.prepareCombinedInput({}, { type: 'text/plain', size: 10 }), /screenshot/)
  assert.throws(() => workflow.prepareCombinedInput({}, { type: 'image/png', size: 0 }), /nonempty/)
})

test('all inputs use OCR then combined endpoint, without pretending to score INR context', async (t) => {
  const requests = [], stages = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    requests.push({ url, options })
    return { ok: true, json: async () => url.endsWith('/check-message') ? { ocr_status: 'ok', ocr_text: 'Screenshot words' } : response }
  })
  const result = await workflow.runCombinedAnalysis({ text: 'Pasted words', url: 'example.com', amount: '25000', when: '2026-09-27T12:00', velocity: '0', call: 'yes' }, imageFile(), (stage) => stages.push(stage))
  assert.equal(requests.length, 2)
  assert.ok(requests[0].options.body instanceof FormData)
  assert.ok(requests[0].options.body.has('image'))
  assert.ok(requests[1].url.endsWith('/check-combined'))
  assert.deepEqual(JSON.parse(requests[1].options.body), { text: 'Pasted words\n\nScreenshot words', url: 'https://example.com/', active_call: true })
  assert.equal(result.context.amount, 25000)
  assert.equal(result.context.velocity, 0)
  assert.equal(result.context.when, '2026-09-27T12:00')
  assert.equal(result.ocr_text, 'Screenshot words')
  assert.equal(result.score, response.score)
  assert.equal(stages.length, 2)
})

test('single evidence channels omit absent fields', async (t) => {
  const requests = []
  t.mock.method(globalThis, 'fetch', async (_url, options) => {
    requests.push(JSON.parse(options.body))
    return { ok: true, json: async () => response }
  })
  await workflow.runCombinedAnalysis({ text: 'hello' })
  await workflow.runCombinedAnalysis({ url: 'https://example.com' })
  assert.deepEqual(requests, [{ text: 'hello' }, { url: 'https://example.com/' }])
})

test('screenshot-only evidence is analyzed; exact duplicated text is not appended twice', async (t) => {
  const messages = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.endsWith('/check-message')) return { ok: true, json: async () => ({ ocr_status: 'ok', ocr_text: 'same words' }) }
    messages.push(JSON.parse(options.body).text)
    return { ok: true, json: async () => response }
  })
  await workflow.runCombinedAnalysis({}, imageFile())
  await workflow.runCombinedAnalysis({ text: 'same words' }, imageFile())
  assert.deepEqual(messages, ['same words', 'same words'])
})

test('unreadable screenshot blocks a misleading partial verdict', async (t) => {
  let calls = 0
  t.mock.method(globalThis, 'fetch', async () => {
    calls += 1
    return { ok: true, json: async () => ({ ocr_status: 'insufficient_text', score: 0 }) }
  })
  await assert.rejects(() => workflow.runCombinedAnalysis({ text: 'otherwise readable' }, imageFile()), /No combined verdict/)
  assert.equal(calls, 1)
})

test('transaction or call context alone is unassessed without a network call', async (t) => {
  t.mock.method(globalThis, 'fetch', () => { throw new Error('Must not call backend') })
  const result = await workflow.runCombinedAnalysis({ amount: '500', call: 'no' })
  assert.equal(result.status, 'unassessed')
  assert.equal(result.score, null)
  const html = renderToStaticMarkup(createElement(Results, { result }))
  assert.match(html, /Unable to assess/)
  assert.match(html, /Transaction risk/)
  assert.match(html, /Unavailable — not scored/)
  assert.doesNotMatch(html, /Low risk|Risk index:.*0 \/ 100/)
})

test('server, malformed-response and network errors reach the workflow', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => ({ ok: false, status: 503, json: async () => ({ detail: 'OCR engine unavailable' }) }))
  await assert.rejects(() => workflow.runCombinedAnalysis({}, imageFile()), /OCR engine unavailable/)
  mock.mock.mockImplementation(async () => ({ ok: true, json: async () => ({}) }))
  await assert.rejects(() => workflow.runCombinedAnalysis({ text: 'hello' }), /incomplete combined result/)
  mock.mock.mockImplementation(async () => { throw new Error('offline') })
  await assert.rejects(() => workflow.runCombinedAnalysis({ text: 'hello' }), /couldn't reach/)
})

test('result includes channel indices, reasons, fallback status and safety action', () => {
  const html = renderToStaticMarkup(createElement(Results, { result: { ...response, status: 'assessed', context: { call: 'yes' } } }))
  for (const text of ['Overall risk: High', '60 / 100', '70 / 100', 'URL risk', 'Message risk', 'Important reasons', 'Suspicious domain', 'Recommended safety action', 'Do not send money', 'fallback scoring rules', 'not a calibrated probability', 'Active call: Yes']) assert.ok(html.includes(text), text)
})
