import { useState } from 'react'

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <header className="max-w-3xl text-center mb-8">
        <h1 className="text-4xl font-bold tracking-tight text-indigo-400 mb-2">
          TrueIntent
        </h1>
        <p className="text-lg text-slate-400">
          Multi-Channel Fraud Intent Verification System
        </p>
      </header>
      
      <main className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl text-center">
        <p className="text-slate-300 mb-4">
          Environment scaffolded successfully with React, Vite, and Tailwind CSS.
        </p>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
          System Ready — Iteration 2 Scaffold
        </span>
      </main>
    </div>
  )
}

export default App
