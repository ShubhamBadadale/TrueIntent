export function LoadingSpinner({ label }) {
  return (
    <div className="mt-6 flex items-center gap-3 rounded-2xl border border-slate-300 bg-white p-5" aria-live="polite">
      <span
        aria-hidden="true"
        className="inline-block h-6 w-6 shrink-0 animate-spin rounded-full border-[3px] border-slate-300 border-t-teal-700"
      />
      <p className="text-lg text-slate-700">{label || 'Analyzing… please wait a moment.'}</p>
    </div>
  )
}

export function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="mt-6 rounded-2xl border-2 border-slate-400 bg-slate-100 p-5 text-left"
    >
      <p className="text-lg font-semibold text-slate-800">Sorry, something did not work.</p>
      <p className="mt-1 text-base leading-relaxed text-slate-700">{message}</p>
    </div>
  )
}

export const inputClass =
  'w-full rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-lg text-slate-900 ' +
  'placeholder:text-slate-400 focus:border-teal-700 focus:outline-none'

export const buttonClass =
  'rounded-xl bg-teal-800 px-6 py-3 text-lg font-semibold text-white ' +
  'hover:bg-teal-900 focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-300 ' +
  'disabled:cursor-not-allowed disabled:opacity-60'

export const labelClass = 'mb-1.5 block text-lg font-medium text-slate-800'
