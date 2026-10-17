import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Dumbbell, ArrowLeft, Home } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4 py-12">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-slate-900 border border-emerald-500/30 text-emerald-400 mb-6 shadow-2xl shadow-emerald-950/60">
        <Dumbbell className="h-10 w-10 animate-pulse" />
      </div>

      <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-3">
        404 ERROR
      </span>

      <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight mb-2">
        Page Not Found
      </h1>

      <p className="text-sm text-slate-400 max-w-md mb-8">
        The route you are trying to access doesn't exist, has been moved, or is temporarily unavailable.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> Go Back
        </button>

        <button
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-5 py-2.5 text-xs font-extrabold shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
        >
          <Home className="h-4 w-4" /> Return to Dashboard
        </button>
      </div>
    </div>
  )
}
