import React, { useEffect, useState } from 'react'
import { Modal } from '../ui/Modal'
import { formAnalysisService } from '../../services/formAnalysisService'
import type { FormAnalysisSessionDetail } from '../../types/formStream'
import { Loader2, AlertCircle, CheckCircle2, Clock, Dumbbell, Award, Flame } from 'lucide-react'

export interface SessionDetailModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string | null
}

export const SessionDetailModal: React.FC<SessionDetailModalProps> = ({
  isOpen,
  onClose,
  sessionId,
}) => {
  const [detail, setDetail] = useState<FormAnalysisSessionDetail | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !sessionId) {
      setDetail(null)
      setError(null)
      return
    }

    let isMounted = true
    setLoading(true)
    setError(null)

    formAnalysisService
      .getSessionDetail(sessionId)
      .then((data) => {
        if (isMounted) {
          setDetail(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || 'Failed to load session details.')
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [isOpen, sessionId])

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '--'
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoStr
    }
  }

  const formatSeconds = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins > 0 ? `${mins}m ` : ''}${secs}s`
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={detail ? detail.exercise_name : 'Session Analysis Detail'}
      description={detail ? `Completed on ${formatDate(detail.completed_at)}` : undefined}
      className="max-w-2xl text-left"
    >
      {loading && (
        <div className="flex flex-col items-center justify-center py-12 space-y-3" role="status">
          <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
          <span className="text-xs text-slate-400 font-medium">Retrieving authoritative session metrics...</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 flex items-start gap-3 my-4">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-rose-200">Unable to load session</h4>
            <p className="text-xs text-rose-300/80">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && detail && (
        <div className="space-y-5 text-slate-200">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider flex items-center gap-1">
                <Award className="h-3 w-3 text-emerald-400" /> Overall Score
              </span>
              <div className="text-xl font-bold font-mono">
                {detail.overall_score !== null ? (
                  <span className="text-emerald-400">{detail.overall_score}%</span>
                ) : (
                  <span className="text-amber-400 text-xs font-semibold">Insufficient Data</span>
                )}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider flex items-center gap-1">
                <Dumbbell className="h-3 w-3 text-cyan-400" /> Reps
              </span>
              <div className="text-xl font-bold font-mono text-slate-100">
                {detail.completed_reps} <span className="text-xs text-slate-400 font-normal">reps</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider flex items-center gap-1">
                <Clock className="h-3 w-3 text-violet-400" /> Duration
              </span>
              <div className="text-xl font-bold font-mono text-slate-100">
                {formatSeconds(detail.duration_seconds)}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider flex items-center gap-1">
                <Flame className="h-3 w-3 text-amber-400" /> Best / Worst
              </span>
              <div className="text-sm font-bold font-mono text-slate-100 mt-1">
                {detail.best_score !== null ? `${detail.best_score}%` : '--'} / {detail.worst_score !== null ? `${detail.worst_score}%` : '--'}
              </div>
            </div>
          </div>

          {/* Rep Count Breakdown Tags */}
          <div className="flex flex-wrap gap-2 text-[11px] font-mono">
            <span className="px-2.5 py-1 rounded-lg bg-emerald-950/50 border border-emerald-800/60 text-emerald-300">
              Valid: {detail.valid_reps}
            </span>
            {detail.incomplete_reps > 0 && (
              <span className="px-2.5 py-1 rounded-lg bg-amber-950/50 border border-amber-800/60 text-amber-300">
                Incomplete: {detail.incomplete_reps}
              </span>
            )}
            {detail.invalid_reps > 0 && (
              <span className="px-2.5 py-1 rounded-lg bg-rose-950/50 border border-rose-800/60 text-rose-300">
                Invalid: {detail.invalid_reps}
              </span>
            )}
            {detail.insufficient_data_reps > 0 && (
              <span className="px-2.5 py-1 rounded-lg bg-slate-800/70 border border-slate-700 text-slate-300">
                Insufficient Data: {detail.insufficient_data_reps}
              </span>
            )}
          </div>

          {/* Category Averages Breakdown */}
          {detail.category_averages && Object.keys(detail.category_averages).length > 0 && (
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2.5">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                Category Score Breakdown
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {Object.entries(detail.category_averages).map(([cat, score]) => (
                  <div key={cat} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1">
                    <span className="text-[10px] text-slate-400 block truncate" title={cat}>
                      {cat}
                    </span>
                    <span className="text-sm font-bold font-mono">
                      {score !== null ? (
                        <span className="text-emerald-400">{score}%</span>
                      ) : (
                        <span className="text-slate-500 font-normal">--</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Deterministic Feedback */}
          {detail.summary_feedback && detail.summary_feedback.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                Summary Feedback
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {detail.summary_feedback.map((fb, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{fb}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rep-by-Rep Breakdown */}
          {detail.reps && detail.reps.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                Repetition Breakdown ({detail.reps.length})
              </h4>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {detail.reps.map((rep) => {
                  const isValid = rep.status.toLowerCase() === 'valid'
                  const isIncomplete = rep.status.toLowerCase() === 'incomplete'
                  const isInsufficient = rep.status.toLowerCase() === 'insufficient_data'

                  return (
                    <div
                      key={rep.rep_number}
                      className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-200">Rep #{rep.rep_number}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                              isValid
                                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                                : isIncomplete
                                ? 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
                                : isInsufficient
                                ? 'bg-slate-800 text-slate-300 border border-slate-700'
                                : 'bg-rose-950/60 text-rose-400 border border-rose-800/50'
                            }`}
                          >
                            {isInsufficient ? 'Insufficient Data' : rep.status}
                          </span>
                        </div>
                        {rep.feedback && rep.feedback.length > 0 && (
                          <p className="text-[11px] text-slate-400">{rep.feedback.join(' · ')}</p>
                        )}
                      </div>

                      <div className="text-right font-mono">
                        {rep.score !== null ? (
                          <span className="text-sm font-bold text-emerald-400">{rep.score}%</span>
                        ) : (
                          <span className="text-xs text-slate-500">--</span>
                        )}
                        {rep.rom_degrees !== null && rep.rom_degrees !== undefined && (
                          <span className="block text-[10px] text-slate-400 font-mono">
                            {Math.round(rep.rom_degrees)}° ROM
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
