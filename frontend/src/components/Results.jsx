import { tierForScore } from '../api.js'

// Calm, solid colors — no flashing, no alarming iconography.
// Soft backgrounds with dark text keep every tier readable and non-dramatic.
const TIER_STYLES = {
  Low: {
    box: 'bg-emerald-50 border-emerald-300',
    badge: 'bg-emerald-700',
    heading: 'text-emerald-950',
    body: 'text-emerald-950',
    guidance:
      'No strong warning signs were found. Take your time anyway — a genuine caller will never mind you waiting or asking someone you trust.',
  },
  Medium: {
    box: 'bg-amber-50 border-amber-300',
    badge: 'bg-amber-600',
    heading: 'text-amber-950',
    body: 'text-amber-950',
    guidance:
      'There are a few things worth a second look. Please pause, read the reasons below, and check with someone you trust before acting.',
  },
  High: {
    box: 'bg-orange-50 border-orange-400',
    badge: 'bg-orange-700',
    heading: 'text-orange-950',
    body: 'text-orange-950',
    guidance:
      'This looks risky. Please stop and do not send any money or share codes. Talk to a family member, or call your bank on its official number.',
  },
  Critical: {
    box: 'bg-red-50 border-red-400',
    badge: 'bg-red-800',
    heading: 'text-red-950',
    body: 'text-red-950',
    guidance:
      'This looks very risky. Please do not send money, share OTPs, or stay on the call. Hang up calmly and speak to someone you trust or your bank.',
  },
}

function toPercent(score) {
  return `${Math.round(Number(score) * 100)} out of 100`
}

/**
 * Shared results card. Accepts Module D unified results
 * ({tier, score, explanation}) as well as single-module results
 * ({score, reasons}) — the tier/explanation are derived when absent.
 */
export default function Results({ result, title }) {
  if (!result) return null
  const score = Number(result.score)
  const tier = result.tier || tierForScore(score)
  const style = TIER_STYLES[tier] || TIER_STYLES.Low
  const explanation =
    result.explanation ||
    (result.reasons && result.reasons.length > 0
      ? result.reasons.join(' ')
      : 'No detailed reasons were returned.')
  const reasons =
    result.explanation && result.reasons && result.reasons.length > 0 ? result.reasons : []

  return (
    <section
      aria-live="polite"
      className={`mt-6 rounded-2xl border-2 p-6 text-left shadow-sm ${style.box}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={`inline-block rounded-full px-4 py-1.5 text-lg font-semibold text-white ${style.badge}`}
        >
          {tier} risk
        </span>
        <span className={`text-lg ${style.body}`}>
          Score: <strong>{toPercent(score)}</strong>
        </span>
      </div>

      {title && <h3 className={`mt-4 text-xl font-semibold ${style.heading}`}>{title}</h3>}

      <p className={`mt-3 text-lg leading-relaxed ${style.body}`}>{explanation}</p>

      {reasons.length > 0 && (
        <ul className={`mt-3 list-disc space-y-1 pl-6 text-base leading-relaxed ${style.body}`}>
          {reasons.slice(0, 6).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}

      <p className={`mt-4 border-t border-black/10 pt-3 text-base leading-relaxed ${style.body}`}>
        {style.guidance}
      </p>
    </section>
  )
}
