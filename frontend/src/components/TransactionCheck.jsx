import { useState } from 'react'
import { checkTransaction } from '../api.js'
import Results from './Results.jsx'
import { ErrorBox, LoadingSpinner, buttonClass, inputClass, labelClass } from './ui.jsx'

function toDateTimeLocalValue(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

export default function TransactionCheck() {
  const [amount, setAmount] = useState('25000')
  const [when, setWhen] = useState(() => toDateTimeLocalValue(new Date()))
  const [deviceId, setDeviceId] = useState('demo-device-01')
  const [isActiveCall, setIsActiveCall] = useState(true)
  const [velocity, setVelocity] = useState('3')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    if (loading) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      // datetime-local has no timezone; interpret it as local time.
      const timestamp = when ? new Date(when).toISOString() : undefined
      setResult(
        await checkTransaction({ amount, timestamp, deviceId, isActiveCall, velocity }),
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-900">Check a money-transfer situation</h2>
      <p className="mt-1 text-lg text-slate-600">
        This is a practice form — it is not connected to your bank. Describe the situation and we
        will explain whether it looks like pressure to pay.
      </p>
      <form onSubmit={onSubmit} className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="txn-amount" className={labelClass}>
            Amount (₹)
          </label>
          <input
            id="txn-amount"
            type="number"
            min="1"
            step="any"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="txn-when" className={labelClass}>
            Date and time
          </label>
          <input
            id="txn-when"
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="txn-device" className={labelClass}>
            Device name (for practice)
          </label>
          <input
            id="txn-device"
            type="text"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="txn-velocity" className={labelClass}>
            Transfers in the last hour
          </label>
          <input
            id="txn-velocity"
            type="number"
            min="0"
            step="1"
            value={velocity}
            onChange={(e) => setVelocity(e.target.value)}
            className={inputClass}
          />
        </div>
        <div className="sm:col-span-2">
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border-2 border-slate-300 bg-white p-4">
            <input
              type="checkbox"
              checked={isActiveCall}
              onChange={(e) => setIsActiveCall(e.target.checked)}
              className="mt-1.5 h-6 w-6 shrink-0 accent-teal-800"
            />
            <span className="text-lg text-slate-800">
              <strong>Are you on a phone call right now?</strong>
              <br />
              <span className="text-slate-600">
                Tick this if someone is on the phone with you while asking for the transfer.
              </span>
            </span>
          </label>
        </div>
        <div className="sm:col-span-2">
          <button type="submit" disabled={loading} className={buttonClass}>
            Check this situation
          </button>
        </div>
      </form>

      {loading && <LoadingSpinner label="Looking at the situation… please wait a moment." />}
      <ErrorBox message={error} />
      {result && <Results result={result} title="Situation check" />}
    </div>
  )
}
