import { useState } from 'react'
import { EMPTY_INPUT, runCombinedAnalysis } from '../combinedAnalysis.js'
import CombinedResults from './CombinedResults.jsx'
import { ErrorBox, LoadingSpinner, buttonClass, inputClass, labelClass } from './ui.jsx'

export default function CombinedCheck() {
  const [values, setValues] = useState({ ...EMPTY_INPUT })
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [fileKey, setFileKey] = useState(0)
  function update(field, value) {
    setValues((previous) => ({ ...previous, [field]: value }))
    setResult(null)
    setError('')
  }
  async function submit(event) {
    event.preventDefault()
    if (loading) return
    setLoading(true)
    setError('')
    setResult(null)
    setStage('Preparing your evidence…')
    try {
      setResult(await runCombinedAnalysis(values, file, setStage))
    } catch (err) {
      setError(err.message || 'Analysis failed. Please retry.')
    } finally {
      setLoading(false)
    }
  }
  function reset() {
    setValues({ ...EMPTY_INPUT }); setFile(null); setFileKey((key) => key + 1)
    setResult(null); setError('')
  }
  return (
    <div>
      <h2 className="text-2xl font-semibold">Combined Fraud Analysis</h2>
      <p className="mt-2 text-lg text-slate-600">Add what you have. All fields are optional; you do not need every type of evidence.</p>
      <form onSubmit={submit} className="mt-6" aria-busy={loading} onInvalid={(event) => { const section = event.target.closest('details'); if (section) section.open = true }}>
        <fieldset disabled={loading} className="space-y-5">
          <legend className="sr-only">Evidence for combined analysis</legend>
          <div>
            <label htmlFor="combined-text" className={labelClass}>Message text (optional)</label>
            <textarea id="combined-text" rows={5} value={values.text} onChange={(e) => update('text', e.target.value)} className={inputClass} placeholder="Paste the message you received" />
          </div>
          <div>
            <label htmlFor="combined-image" className={labelClass}>Screenshot (optional)</label>
            <p id="screenshot-help" className="mb-2 text-slate-600">PNG, JPEG, WebP or BMP, up to 10 MB. Readable screenshot text is combined with your pasted message.</p>
            <input key={fileKey} id="combined-image" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" aria-describedby="screenshot-help" className={inputClass}
              onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setError('') }} />
            {file && <button type="button" className="mt-2 text-teal-800 underline" onClick={() => { setFile(null); setFileKey((key) => key + 1); setResult(null); setError('') }}>Remove screenshot</button>}
          </div>
          <div>
            <label htmlFor="combined-url" className={labelClass}>Suspicious URL (optional)</label>
            <input id="combined-url" type="text" inputMode="url" autoComplete="off" value={values.url} onChange={(e) => update('url', e.target.value)} className={inputClass} placeholder="https://example.com" />
          </div>
          <details className="rounded-2xl border border-slate-300 p-4">
            <summary className="cursor-pointer text-lg font-semibold">Transaction details and active-call status (optional)</summary>
            <p id="context-help" className="my-3 text-slate-600">Transaction details remain display-only because transaction risk is unavailable. A reported Yes or No call status accompanies message/link analysis as experimental context; it is not verified call telemetry.</p>
            <div className="grid gap-4 sm:grid-cols-2" aria-describedby="context-help">
              <div><label htmlFor="combined-amount" className={labelClass}>Amount (INR)</label><input id="combined-amount" type="number" min="0.01" step="any" value={values.amount} onChange={(e) => update('amount', e.target.value)} className={inputClass} /></div>
              <div><label htmlFor="combined-when" className={labelClass}>Date and local time</label><input id="combined-when" type="datetime-local" value={values.when} onChange={(e) => update('when', e.target.value)} className={inputClass} /></div>
              <div><label htmlFor="combined-velocity" className={labelClass}>Transfers in the last hour</label><input id="combined-velocity" type="number" min="0" step="1" value={values.velocity} onChange={(e) => update('velocity', e.target.value)} className={inputClass} /></div>
              <div><label htmlFor="combined-call" className={labelClass}>Are you on a call?</label><select id="combined-call" value={values.call} onChange={(e) => update('call', e.target.value)} className={inputClass}><option value="">Not provided</option><option value="yes">Yes</option><option value="no">No</option><option value="unknown">Not sure</option></select></div>
            </div>
          </details>
          <div className="flex flex-wrap gap-3">
            <button type="submit" className={buttonClass}>{loading ? 'Analyzing…' : 'Analyze combined evidence'}</button>
            <button type="button" onClick={reset} className="rounded-xl border-2 border-slate-300 px-5 py-3 text-lg">Clear all</button>
          </div>
        </fieldset>
      </form>
      {loading && <LoadingSpinner label={stage} />}
      <ErrorBox message={error} />
      {result && <CombinedResults result={result} />}
    </div>
  )
}
