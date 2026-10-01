import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

let server
before(async () => {
  server = await createServer({ server: { middlewareMode: true, watch: null, ws: false }, appType: 'custom' })
})
after(async () => { await server?.close() })

test('missing and unreadable results never display low risk', async () => {
  const { default: Results } = await server.ssrLoadModule('/src/components/Results.jsx')
  for (const result of [{ score: null }, { score: NaN }, { score: 2 }, { score: 0, text_assessed: false }, { score: 0, ocr_status: 'insufficient_text' }]) {
    const html = renderToStaticMarkup(createElement(Results, { result }))
    assert.match(html, /Unable to assess/)
    assert.doesNotMatch(html, /Low risk|out of 100/)
  }
})

test('risk index wording and tier boundaries are explicit', async () => {
  const { default: Results } = await server.ssrLoadModule('/src/components/Results.jsx')
  const { tierForScore } = await server.ssrLoadModule('/src/api.js')
  assert.deepEqual([0, .2499, .25, .5, .75, 1].map(tierForScore), ['Low', 'Low', 'Medium', 'High', 'Critical', 'Critical'])
  for (const invalid of [null, NaN, Infinity, -1, 2, '0']) assert.equal(tierForScore(invalid), null)
  const html = renderToStaticMarkup(createElement(Results, { result: { score: .6 } }))
  assert.match(html, /Risk Index/)
  assert.match(html, /Verdict: Likely scam/)
  assert.match(html, /not a calibrated probability/)
})

test('benchmark form has explicit source units and no misleading telemetry controls', async () => {
  const { default: TransactionCheck } = await server.ssrLoadModule('/src/components/TransactionCheck.jsx')
  const html = renderToStaticMarkup(createElement(TransactionCheck))
  assert.match(html, /Original IEEE-CIS amount \(source units\)/)
  assert.match(html, /Real money-transfer assessment is unavailable/)
  assert.doesNotMatch(html, /datetime-local|type="checkbox"|txn-device|txn-velocity|Amount \(₹\)/)
})

test('benchmark results have no real-transfer risk tier or advice', async () => {
  const { default: Results } = await server.ssrLoadModule('/src/components/Results.jsx')
  const html = renderToStaticMarkup(createElement(Results, { result: {
    analysis_scope: 'ieee_cis_amount_only_benchmark', score: .01,
    explanation: 'Source-unit benchmark only.',
  } }))
  assert.match(html, /IEEE-CIS benchmark result/)
  assert.match(html, /0.0100/)
  assert.doesNotMatch(html, /Low risk|No strong warning|out of 100/)
})

test('client requires explicit source-unit opt-in and sends no timestamp conversion', async (t) => {
  const { checkTransaction } = await server.ssrLoadModule('/src/api.js')
  const requests = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    requests.push({ url, payload: JSON.parse(options.body) })
    return { ok: true, json: async () => ({ score: .1 }) }
  })
  await checkTransaction({ amount: '5.25', amountUnit: 'ieee_cis_source', timestamp: 'local', isActiveCall: true })
  assert.deepEqual(requests[0].payload, { amount: 5.25, amount_unit: 'ieee_cis_source' })
  assert.match(requests[0].url, /\/check-transaction$/)
  await checkTransaction({ amount: '500' })
  assert.equal(requests[1].payload.amount_unit, 'INR')
})
