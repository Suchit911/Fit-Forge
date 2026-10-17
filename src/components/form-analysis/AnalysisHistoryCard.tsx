import React from 'react'
import type { FormAnalysisSessionSummary } from '../../types/formStream'
import { Play, AlertCircle, Dumbbell } from 'lucide-react'

export interface AnalysisHistoryCardProps {
  history: FormAnalysisSessionSummary[]
  onSelectSession?: (sessionId: string) => void
  loading?: boolean
  error?: string | null
}

export const AnalysisHistoryCard: React.FC<AnalysisHistoryCardProps> = ({
  history,
  onSelectSession,
  loading = false,
  error = null,
}) => {
  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '--'
    try {
      const d = new Date(isoStr)
      if (isNaN(d.getTime())) return isoStr
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    } catch {
      return isoStr
    }
  }

  const formatTime = (isoStr?: string) => {
    if (!isoStr) return ''
    try {
      const d = new Date(isoStr)
      if (isNaN(d.getTime())) return ''
      return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Analysis History</h3>
        {history.length > 0 && (
          <span className="text-[10px] font-mono font-semibold text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
            {history.length} {history.length === 1 ? 'Session' : 'Sessions'}
          </span>
        )}
      </div>

      {loading && (
        <div className="py-8 text-center text-xs text-slate-400 animate-pulse">
          Loading analysis history...
        </div>
      )}

      {error && !loading && (
        <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800/50 flex items-center gap-2 text-rose-300 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="py-8 text-center space-y-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/60 mx-auto text-slate-400">
            <Dumbbell className="h-5 w-5" />
          </div>
          <p className="text-xs text-slate-400 font-medium">No recorded form sessions yet.</p>
          <p className="text-[11px] text-slate-500">Completed workouts with &ge;1 rep will appear here.</p>
        </div>
      )}

      {!loading && !error && history.length > 0 && (
        <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
          {history.map((item) => {
            const hasScore = item.overall_score !== null && item.overall_score !== undefined
            const timeStr = formatTime(item.completed_at || item.started_at)
            const dateStr = formatDate(item.completed_at || item.started_at)

            return (
              <div
                key={item.session_id}
                onClick={() => onSelectSession?.(item.session_id)}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors group cursor-pointer"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelectSession?.(item.session_id)
                  }
                }}
              >
                <div className="space-y-0.5 min-w-0 pr-2">
                  <span className="text-[10px] text-slate-400 font-mono block truncate">
                    {dateStr} {timeStr ? `· ${timeStr}` : ''}
                  </span>
                  <h4 className="text-xs font-bold text-slate-200 group-hover:text-emerald-400 transition-colors truncate">
                    {item.exercise_name} · {item.completed_reps} {item.completed_reps === 1 ? 'rep' : 'reps'}
                  </h4>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {hasScore ? (
                    <span className="text-xs font-extrabold font-mono text-emerald-400">
                      {item.overall_score}%
                    </span>
                  ) : (
                    <span
                      className="text-[11px] font-semibold font-mono text-slate-400"
                      title="Insufficient valid repetitions to compute numerical score"
                    >
                      --
                    </span>
                  )}
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 group-hover:border-emerald-500 group-hover:text-emerald-400 transition-colors">
                    <Play className="h-3 w-3 fill-current ml-0.5" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
