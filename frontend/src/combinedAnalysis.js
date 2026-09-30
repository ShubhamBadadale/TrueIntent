import { checkCombined, checkMessageImage } from './api.js'

export const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/bmp']
export const EMPTY_INPUT = { amount: '', when: '', velocity: '', call: '', text: '', url: '' }

export function prepareCombinedInput(values, file) {
  const text = (values.text || '').trim()
  const rawUrl = (values.url || '').trim()
  const context = {}
  for (const [field, label] of [['amount', 'Amount'], ['velocity', 'Transfers in the last hour']]) {
    const raw = (values[field] ?? '').toString().trim()
    if (!raw) continue
    const number = Number(raw)
    if (!Number.isFinite(number) || number < 0 || (field === 'amount' && number === 0)
      || (field === 'velocity' && !Number.isSafeInteger(number))) {
      throw new Error(`${label} must be ${field === 'amount' ? 'a positive number' : 'a nonnegative whole number'}.`)
    }
    context[field] = number
  }
  if (values.when) {
    if (Number.isNaN(new Date(values.when).getTime())) throw new Error('Enter a valid date and time.')
    context.when = values.when // Display-only local time; never converted into model features.
  }
  if (values.call && !['yes', 'no', 'unknown'].includes(values.call)) throw new Error('Choose a valid call status.')
  if (values.call) context.call = values.call
  let url
  if (rawUrl) {
    try {
      if (/\s/.test(rawUrl)) throw new Error()
      const candidate = new URL(rawUrl.includes('://') ? rawUrl : `https://${rawUrl}`)
      if (!['http:', 'https:'].includes(candidate.protocol) || !candidate.hostname.includes('.')) throw new Error()
      url = candidate.href
    } catch {
      throw new Error('Enter a valid HTTP or HTTPS website link, such as https://example.com.')
    }
  }
  if (file && (!IMAGE_TYPES.includes(file.type) || file.size <= 0 || file.size > 10 * 1024 * 1024)) {
    throw new Error('Choose a nonempty PNG, JPEG, WebP or BMP screenshot up to 10 MB.')
  }
  if (!text && !url && !file && !Object.keys(context).length) {
    throw new Error('Add a message, screenshot, link or transaction/call context before analyzing.')
  }
  return { text, url, context }
}

export async function runCombinedAnalysis(values, file, onStage = () => {}) {
  const { text, url, context } = prepareCombinedInput(values, file)
  let extracted = ''
  if (file) {
    onStage('Reading your screenshot…')
    const image = await checkMessageImage(file)
    if (image.ocr_status !== 'ok' || !image.ocr_text?.trim()) {
      throw new Error('We could not read the screenshot reliably. Upload a clearer image, paste its text, or remove it to analyze the other evidence. No combined verdict was issued.')
    }
    extracted = image.ocr_text.trim()
  }
  const message = [...new Set([text, extracted].filter(Boolean))].join('\n\n')
  if (!message && !url) {
    return { status: 'unassessed', context, modules: {}, score: null, tier: null }
  }
  onStage('Combining the message and link evidence…')
  // Real transaction scoring is disabled. Do not relabel INR as dataset units,
  // or silently send it to the incompatible transaction-fusion route.
  const result = await checkCombined({ ...(message ? { text: message } : {}), ...(url ? { url } : {}),
    ...(['yes', 'no'].includes(context.call) ? { active_call: context.call === 'yes' } : {}) })
  if (!['Low', 'Medium', 'High', 'Critical'].includes(result.tier)
      || typeof result.score !== 'number' || !Number.isFinite(result.score)
      || result.score < 0 || result.score > 1 || !result.modules || typeof result.modules !== 'object') {
    throw new Error('The server returned an incomplete combined result. Please retry.')
  }
  return { ...result, status: 'assessed', context, ocr_text: extracted }
}
