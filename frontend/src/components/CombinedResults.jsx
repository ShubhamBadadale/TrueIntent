const COLORS = { Low: 'border-emerald-300 bg-emerald-50', Medium: 'border-amber-300 bg-amber-50', High: 'border-orange-400 bg-orange-50', Critical: 'border-red-400 bg-red-50' }
const ACTIONS = {
  Low: 'No strong warning signs were found in the analyzed evidence. This does not verify the recipient or make a transfer safe. Verify independently before paying.',
  Medium: 'Pause the transfer. Verify the request through an official number or someone you trust before continuing.',
  High: 'Do not send money or share codes. Contact your bank through its official number and ask someone you trust to help check the request.',
  Critical: 'Stop the interaction. Do not send money or share OTPs. End a pressuring call and contact your bank through its official number.',
}
const index = (score) => `${Math.round(score * 100)} / 100`

function RiskCard({ label, module, unavailable }) {
  const valid = module?.text_assessed !== false && typeof module?.score === 'number' && Number.isFinite(module.score) && module.score >= 0 && module.score <= 1
  return <div className="rounded-xl border border-slate-300 bg-white p-4">
    <h4 className="font-semibold">{label}</h4>
    <p className="mt-1 text-lg">{unavailable || (valid ? index(module.score) : 'Not assessed')}</p>
    {module?.ml_status?.startsWith('rules_only') && <p className="mt-1 text-sm text-slate-600">Rule-based checks only; classifier unavailable.</p>}
    {module?.ml_status?.includes('limited real-language coverage') && <p className="mt-1 text-sm text-slate-600">Experimental intent model with limited real-language coverage.</p>}
    {module?.ml_status?.startsWith('unavailable') && <p className="mt-1 text-sm text-slate-600">This channel could not be assessed; the score shown is not a low-risk verdict.</p>}
  </div>
}

export default function CombinedResults({ result }) {
  const assessed = result.status === 'assessed'
  const modules = result.modules || {}
  const context = result.context || {}
  const reasons = [...new Set(Object.values(modules).flatMap((module) => module.reasons || []))].filter((reason) => typeof reason === 'string')
  return (
    <section aria-live="polite" className={`mt-6 rounded-2xl border-2 p-6 ${assessed ? COLORS[result.tier] : 'border-slate-300 bg-slate-50'}`}>
      <h3 className="text-2xl font-semibold">Overall risk: {assessed ? result.tier : 'Unable to assess'}</h3>
      <p className="mt-2 text-lg">Risk Index: <strong>{assessed ? index(result.score) : 'Not available'}</strong></p>
      <p className="mt-2 text-slate-700">Based on submitted message, readable screenshot text, URL and known call status. This index is not a calibrated probability of fraud.</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <RiskCard label="Transaction risk" unavailable="Unavailable — not scored" />
        <RiskCard label="URL risk" module={modules.module_b} />
        <RiskCard label="Message risk" module={modules.module_c} />
      </div>
      {modules.module_c && <p className="mt-2 text-sm text-slate-600">Message risk includes any embedded links. A separate URL score appears only when a URL was submitted in the URL field.</p>}
      {result.details?.scoring_method === 'fixed_weights_missing_model' && <p className="mt-3 text-slate-700">The combined model is unavailable. This result uses the backend’s fallback scoring rules.</p>}
      {result.details?.model_caveat && <p className="mt-2 text-sm text-slate-600">{result.details.model_caveat}</p>}
      <h4 className="mt-5 text-lg font-semibold">Important reasons</h4>
      <p className="mt-2">{assessed ? result.explanation : 'Transaction details and call status alone cannot currently be scored. Add a message, readable screenshot or URL.'}</p>
      {reasons.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5">{reasons.slice(0, 8).map((reason) => <li key={reason}>{reason}</li>)}</ul>}
      {Object.keys(context).length > 0 && <div className="mt-5 rounded-xl border border-slate-300 p-4">
        <h4 className="font-semibold">Your reported context</h4>
        <p>Transaction details are not scored or sent. Known call status accompanies the experimental fusion analysis.</p>
        {context.amount !== undefined && <p>Amount: ₹{context.amount.toLocaleString('en-IN')}</p>}
        {context.when && <p>Local date/time: {context.when.replace('T', ' ')}</p>}
        {context.velocity !== undefined && <p>Transfers in the last hour: {context.velocity}</p>}
        {context.call && <p>Active call: {{ yes: 'Yes', no: 'No', unknown: 'Not sure' }[context.call]}</p>}
      </div>}
      {result.ocr_text && <details className="mt-4"><summary className="cursor-pointer font-semibold">Text read from your screenshot</summary><p className="mt-2 whitespace-pre-wrap break-words">{result.ocr_text}</p></details>}
      <div className="mt-5 border-t border-slate-300 pt-4">
        <h4 className="text-lg font-semibold">Recommended safety action</h4>
        <p className="mt-2">{assessed ? ACTIONS[result.tier] : 'Pause and independently verify the recipient before transferring. An unavailable assessment is not a safe verdict.'}</p>
        {context.call === 'yes' && <p className="mt-2">If the caller is pressuring you, end the call and verify using an official number.</p>}
      </div>
    </section>
  )
}
