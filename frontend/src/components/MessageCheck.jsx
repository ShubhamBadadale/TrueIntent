import { useState } from 'react'
import { checkMessageImage, checkMessageText } from '../api.js'
import Results from './Results.jsx'
import { ErrorBox, LoadingSpinner, buttonClass, inputClass, labelClass } from './ui.jsx'

const tabClass = (active) =>
  `rounded-xl px-5 py-2.5 text-lg font-medium focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-300 ${
    active ? 'bg-teal-800 text-white' : 'bg-slate-200 text-slate-800 hover:bg-slate-300'
  }`

export default function MessageCheck() {
  const [mode, setMode] = useState('text') // 'text' | 'image'
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const canSubmit = mode === 'text' ? text.trim().length > 0 && !loading : file !== null && !loading

  async function onSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      if (mode === 'text') {
        setResult(await checkMessageText(text.trim()))
      } else {
        setResult(await checkMessageImage(file))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function switchMode(next) {
    setMode(next)
    setError('')
    setResult(null)
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-900">Check a message or screenshot</h2>
      <p className="mt-1 text-lg text-slate-600">
        Paste a message you received, or upload a photo of the chat. We read it and explain calmly what to notice.
      </p>

      <div className="mt-4 flex gap-2" role="tablist" aria-label="Message input type">
        <button type="button" role="tab" aria-selected={mode === 'text'} onClick={() => switchMode('text')} className={tabClass(mode === 'text')}>
          Write or paste message
        </button>
        <button type="button" role="tab" aria-selected={mode === 'image'} onClick={() => switchMode('image')} className={tabClass(mode === 'image')}>
          Upload screenshot
        </button>
      </div>

      <form onSubmit={onSubmit} className="mt-4">
        {mode === 'text' ? (
          <>
            <label htmlFor="msg-text" className={labelClass}>
              Message text
            </label>
            <textarea
              id="msg-text"
              rows={5}
              placeholder="Paste the message here…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className={`${inputClass} resize-y`}
            />
          </>
        ) : (
          <>
            <label htmlFor="msg-image" className={labelClass}>
              Chat screenshot (PNG or JPEG, up to 10 MB)
            </label>
            <input
              id="msg-image"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/bmp"
              onChange={(e) => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
              className="block w-full text-lg text-slate-700 file:mr-4 file:rounded-xl file:border-0 file:bg-teal-800 file:px-5 file:py-2.5 file:text-lg file:font-semibold file:text-white hover:file:bg-teal-900"
            />
            {file && <p className="mt-2 text-base text-slate-600">Selected: {file.name}</p>}
          </>
        )}
        <button type="submit" disabled={!canSubmit} className={`${buttonClass} mt-4`}>
          Check this message
        </button>
      </form>

      {loading && <LoadingSpinner label="Reading the message… please wait a moment." />}
      <ErrorBox message={error} />
      {result && result.ocr_text && (
        <div className="mt-6 rounded-2xl border border-slate-300 bg-white p-5 text-left">
          <h3 className="text-lg font-semibold text-slate-800">Text we read from your screenshot</h3>
          <p className="mt-1 whitespace-pre-wrap text-base leading-relaxed text-slate-700">{result.ocr_text}</p>
        </div>
      )}
      {result && <Results result={result} title="Message check" />}
    </div>
  )
}
