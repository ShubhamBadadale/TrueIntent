import { useState } from 'react'
import { checkUrl } from '../api.js'
import Results from './Results.jsx'
import { ErrorBox, LoadingSpinner, buttonClass, inputClass, labelClass } from './ui.jsx'

export default function LinkCheck() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    if (!url.trim() || loading) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await checkUrl(url.trim()))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-900">Check a link</h2>
      <p className="mt-1 text-lg text-slate-600">
        Paste a link you were sent. We will check it quietly and explain what we find in plain words.
      </p>
      <form onSubmit={onSubmit} className="mt-4">
        <label htmlFor="link-url" className={labelClass}>
          Website link
        </label>
        <input
          id="link-url"
          type="text"
          inputMode="url"
          autoComplete="off"
          placeholder="https://example.com/login"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className={inputClass}
        />
        <button type="submit" disabled={loading || !url.trim()} className={`${buttonClass} mt-4`}>
          Check this link
        </button>
      </form>

      {loading && <LoadingSpinner label="Checking the link… please wait a moment." />}
      <ErrorBox message={error} />
      {result && <Results result={result} title="Link check" />}
    </div>
  )
}
