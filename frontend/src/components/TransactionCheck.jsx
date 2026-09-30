import { useState } from 'react'
import { checkTransaction } from '../api.js'
import Results from './Results.jsx'
import { ErrorBox, LoadingSpinner, buttonClass, inputClass, labelClass } from './ui.jsx'

export default function TransactionCheck() {
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    if (loading || amount.trim() === '') return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await checkTransaction({ amount, amountUnit: 'ieee_cis_source' }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-900">IEEE-CIS transaction benchmark</h2>
      <p className="mt-2 text-lg text-slate-600">
        Real money-transfer assessment is unavailable. This research benchmark accepts an
        original IEEE-CIS dataset amount in its source units. Do not enter an INR transfer
        or convert it using an exchange rate.
      </p>
      <p className="mt-2 text-lg text-slate-600">
        Time, device familiarity, call state and transfer count are excluded because the
        training data does not support those signals for this use.
      </p>
      <form onSubmit={onSubmit} className="mt-4">
        <label htmlFor="txn-amount" className={labelClass}>Original IEEE-CIS amount (source units)</label>
        <input
          id="txn-amount"
          type="number"
          min="0"
          step="any"
          required
          value={amount}
          onChange={(e) => { setAmount(e.target.value); setResult(null) }}
          className={inputClass}
        />
        <button type="submit" disabled={loading || !amount.trim()} className={buttonClass + ' mt-4'}>
          Run amount-only benchmark
        </button>
      </form>
      {loading && <LoadingSpinner label="Running the benchmark..." />}
      <ErrorBox message={error} />
      {result && <Results result={result} title="Benchmark result" />}
    </div>
  )
}
