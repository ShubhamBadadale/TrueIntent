import { useState } from 'react'
import LinkCheck from './components/LinkCheck.jsx'
import MessageCheck from './components/MessageCheck.jsx'
import TransactionCheck from './components/TransactionCheck.jsx'
import CombinedCheck from './components/CombinedCheck.jsx'

const TABS = [
  { id: 'combined', label: 'Combined Fraud Analysis', hint: 'Bring your evidence together' },
  { id: 'link', label: 'Check a Link', hint: 'A website or login link' },
  { id: 'message', label: 'Check a Message / Screenshot', hint: 'A chat, SMS, or photo of one' },
  { id: 'transaction', label: 'Transaction Benchmark', hint: 'IEEE-CIS source amounts only' },
]

export default function App() {
  const [tab, setTab] = useState('combined')

  return (
    <div className="min-h-screen bg-[#faf8f3] text-slate-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-3xl px-5 py-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-teal-900">TrueIntent</h1>
          <p className="mt-2 text-xl text-slate-600">
            Pause together. Check before you send.
          </p>
          <p className="mx-auto mt-3 max-w-2xl text-lg leading-relaxed text-slate-600">
            Bring together a message, screenshot and suspicious link to understand the warning
            signs before you act. You can also describe the transaction and call for context.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 pb-16">
        <nav aria-label="What to check" className="mt-6 grid gap-2 sm:grid-cols-2">
          {TABS.map((t) => {
            const active = tab === t.id
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                aria-pressed={active}
                className={`rounded-2xl border-2 px-4 py-3 text-left focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-300 ${
                  active
                    ? 'border-teal-800 bg-teal-800 text-white shadow-sm'
                    : 'border-stone-300 bg-white text-slate-800 hover:border-teal-600'
                }`}
              >
                <span className="block text-lg font-semibold">{t.label}</span>
                <span className={`block text-base ${active ? 'text-teal-100' : 'text-slate-500'}`}>
                  {t.hint}
                </span>
              </button>
            )
          })}
        </nav>

        <div className="mt-6 rounded-3xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
          {tab === 'combined' && <CombinedCheck />}
          {tab === 'link' && <LinkCheck />}
          {tab === 'message' && <MessageCheck />}
          {tab === 'transaction' && <TransactionCheck />}
        </div>

        <footer className="mt-8 text-center text-base leading-relaxed text-slate-500">
          <p>
            TrueIntent is a learning demonstration, not financial advice. When in doubt, stop, hang
            up calmly, and call your bank on its official number — or ask someone you trust.
          </p>
        </footer>
      </main>
    </div>
  )
}
