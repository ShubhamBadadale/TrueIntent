// TrueIntent API client. Backend defaults to http://localhost:8000
// (override with VITE_API_URL, e.g. `VITE_API_URL=http://localhost:8000 npm run dev`).

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const SERVER_UNREACHABLE =
  "We couldn't reach the analysis server. Please make sure the backend is running " +
  '(python run-backend.ps1, http://localhost:8000) and try again.'

function humanizeDetail(detail, fallback) {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((e) => {
        const field = (e.loc || []).filter((p) => p !== 'body').join('.')
        return field ? `${field}: ${e.msg}` : e.msg
      })
      .filter(Boolean)
    if (msgs.length > 0) return msgs.join(' ')
  }
  return fallback
}

async function request(path, { method = 'GET', json, form } = {}) {
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      ...(json ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(json) } : {}),
      ...(form ? { body: form } : {}),
    })
  } catch {
    throw new Error(SERVER_UNREACHABLE)
  }
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const statusHint =
      res.status === 503
        ? ' The service is temporarily unavailable — please try again in a moment.'
        : ''
    throw new Error(
      humanizeDetail(data && data.detail, `The server returned an error (${res.status}).`) + statusHint,
    )
  }
  return data
}

export function checkUrl(url) {
  return request('/check-url', { method: 'POST', json: { url } })
}

export function checkMessageText(text) {
  const form = new FormData()
  form.append('text', text)
  return request('/check-message', { method: 'POST', form })
}

export function checkMessageImage(file) {
  const form = new FormData()
  form.append('image', file)
  return request('/check-message', { method: 'POST', form })
}

export function checkTransaction({ amount, timestamp, deviceId, isActiveCall, velocity }) {
  const payload = {
    amount: Number(amount),
    device_id: deviceId,
    is_active_call: Boolean(isActiveCall),
    transaction_velocity: Number(velocity),
  }
  if (timestamp) payload.timestamp = timestamp
  return request('/check-transaction', { method: 'POST', json: payload })
}

/** Same cutoffs as the backend (Module D) so single-module scores get a tier. */
export function tierForScore(score) {
  if (score < 0.25) return 'Low'
  if (score < 0.5) return 'Medium'
  if (score < 0.75) return 'High'
  return 'Critical'
}
