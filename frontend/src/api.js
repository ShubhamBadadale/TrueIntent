// TrueIntent API client. Backend defaults to http://localhost:8000
// (override with VITE_API_URL, e.g. `VITE_API_URL=http://localhost:8000 npm run dev`).

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const SERVER_UNREACHABLE =
  "We couldn't reach the analysis server. Please make sure the backend is running " +
  '(run .\\run-backend.ps1, http://localhost:8000) and try again.'

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
  let data = null
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 90000)
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      signal: controller.signal,
      ...(json ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(json) } : {}),
      ...(form ? { body: form } : {}),
    })
    try {
      data = await res.json()
    } catch (error) {
      if (controller.signal.aborted) throw error
    }
  } catch {
    if (controller.signal.aborted) throw new Error('Analysis took too long. Please try again or paste the screenshot text.')
    throw new Error(SERVER_UNREACHABLE)
  } finally {
    clearTimeout(timer)
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
  if (!data || typeof data !== 'object') throw new Error('The server returned an unreadable response. Please retry.')
  return data
}

export function checkCombined(payload) {
  return request('/check-combined', { method: 'POST', json: payload })
}

export function checkUrl(url) {
  return request('/check-url', { method: 'POST', json: { url } })
}

export function checkMessageText(text) {
  if (text.length > 20000) throw new Error('Message exceeds the 20,000 character limit.')
  const form = new FormData()
  form.append('text', text)
  return request('/check-message', { method: 'POST', form })
}

export function checkMessageImage(file) {
  if (!file || !['image/png', 'image/jpeg', 'image/webp', 'image/bmp'].includes(file.type)) throw new Error('Upload a PNG, JPEG, WebP or BMP screenshot.')
  if (!file.size || file.size > 10 * 1024 * 1024) throw new Error('Screenshot must be nonempty and at most 10 MB.')
  const form = new FormData()
  form.append('image', file)
  return request('/check-message', { method: 'POST', form })
}

export function checkTransaction({ amount, amountUnit = 'INR' }) {
  const payload = {
    amount: Number(amount),
    amount_unit: amountUnit,
  }
  return request('/check-transaction', { method: 'POST', json: payload })
}

/** Same cutoffs as the backend (Module D) so single-module scores get a tier. */
export function tierForScore(score) {
  if (typeof score !== 'number' || !Number.isFinite(score) || score < 0 || score > 1) return null
  if (score < 0.25) return 'Low'
  if (score < 0.5) return 'Medium'
  if (score < 0.75) return 'High'
  return 'Critical'
}
