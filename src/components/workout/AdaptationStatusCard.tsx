import React from 'react'
import { Sparkles, ArrowRight, CheckCircle2, History } from 'lucide-react'
import { Badge } from '../ui/Badge.tsx'
import type { EffectivePrescriptionResponse, ProgramResponse } from '../../types/program.ts'
import {
  formatAdaptationType,
  formatRuleCode,
  formatAdaptationDate,
  extractMetricComparisons,
  formatExerciseDisplayName,
} from '../../utils/adaptationFormatting.ts'

export interface AdaptationStatusCardProps {
  prescription?: EffectivePrescriptionResponse | null
  program?: ProgramResponse | null
  week: number
  day: number
  onOpenHistory?: () => void
}

export const AdaptationStatusCard: React.FC<AdaptationStatusCardProps> = ({
  prescription,
  program,
  week,
  day,
  onOpenHistory,
}) => {
  const isAdapted = Boolean(prescription?.isAdapted || prescription?.is_adapted)
  const appliedAdaptations = prescription?.appliedAdaptations || prescription?.applied_adaptations || []
  const planVersion = prescription?.planVersion ?? prescription?.plan_version ?? program?.planVersion ?? 1
  const totalProgramAdaptations =
    program?.adaptationHistory?.length || program?.adaptation_history?.length || 0

  // 1. Not Adapted State: Factual, non-medical presentation
  if (!isAdapted || appliedAdaptations.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm text-left flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800 text-slate-400 border border-slate-700 shrink-0 mt-0.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-bold text-slate-200">No adaptive changes</h4>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                Plan v{planVersion}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5 break-words">
              Your current workout follows the active program prescription.
            </p>
          </div>
        </div>

        {onOpenHistory && (
          <button
            type="button"
            onClick={onOpenHistory}
            className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold text-slate-300 hover:text-emerald-400 border border-slate-700 hover:border-emerald-500/40 rounded-xl px-3 py-2 bg-slate-800/60 transition-colors shrink-0 cursor-pointer self-start sm:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            aria-label="View program adaptation history"
          >
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Adaptation History {totalProgramAdaptations > 0 && `(${totalProgramAdaptations})`}</span>
          </button>
        )}
      </div>
    )
  }

  // 2. Adapted Prescription State: Prominent, authoritative presentation
  return (
    <div className="rounded-2xl border border-cyan-500/30 bg-slate-900/90 p-5 sm:p-6 backdrop-blur-sm space-y-4 text-left shadow-lg shadow-cyan-950/20">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Adaptive Update</span>
          </span>
          <span className="text-xs font-mono font-semibold text-slate-300 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700">
            Week {week} · Day {day}
          </span>
          <span className="text-xs font-mono text-cyan-300 bg-cyan-950/60 px-2.5 py-0.5 rounded-full border border-cyan-800/40">
            Program Version v{planVersion}
          </span>
        </div>

        {onOpenHistory && (
          <button
            type="button"
            onClick={onOpenHistory}
            className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold text-slate-300 hover:text-cyan-300 border border-slate-700 hover:border-cyan-500/40 rounded-xl px-3 py-2 bg-slate-800/60 transition-colors shrink-0 cursor-pointer self-start sm:self-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            aria-label="View complete adaptation history"
          >
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span>All Adaptations {totalProgramAdaptations > 0 && `(${totalProgramAdaptations})`}</span>
          </button>
        )}
      </div>

      {/* Applied Adaptations for this Day */}
      <div className="space-y-3">
        {appliedAdaptations.map((ad, idx) => {
          const typeMeta = formatAdaptationType(ad.adaptationType || ad.adaptation_type)
          const ruleTitle = formatRuleCode(ad.ruleCode || ad.rule_code)
          const exName = formatExerciseDisplayName(ad.affectedExerciseId || ad.affected_exercise_id || ad.exerciseId || ad.exercise_id)
          const dateStr = formatAdaptationDate(ad.appliedAt || ad.applied_at)
          const comparisons = extractMetricComparisons(
            ad.previousPrescription || ad.previous_prescription,
            ad.appliedPrescription || ad.applied_prescription || ad.proposedPrescription || ad.proposed_prescription
          )

          return (
            <div
              key={ad.decisionId || idx}
              className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3"
            >
              {/* Exercise and Rule Title */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="min-w-0">
                  <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <span className="text-cyan-400 font-mono text-xs" aria-hidden="true">●</span>
                    <span className="break-words">{exName}</span>
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5 break-words">
                    Reason: <span className="text-slate-300">{ruleTitle}</span>
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <Badge variant={typeMeta.badgeVariant}>
                    {typeMeta.label}
                  </Badge>
                  <span className="text-[11px] font-mono text-slate-400">
                    Applied: {dateStr}
                  </span>
                </div>
              </div>

              {/* Metric Changes (e.g. Load 50 kg → 52.5 kg) */}
              {comparisons.length > 0 && (
                <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                  {comparisons.map((c, cIdx) => (
                    <div
                      key={cIdx}
                      className="rounded-lg bg-slate-900 border border-slate-800 p-2.5 text-left"
                    >
                      <span className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                        {c.metric}
                      </span>
                      <div className="flex items-center gap-2 text-xs font-bold font-mono mt-0.5">
                        <span className="text-slate-400 line-through">{c.before}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400 shrink-0" aria-hidden="true" />
                        <span className="text-emerald-400 font-bold">{c.after}</span>
                        <span className="sr-only"> changed from {c.before} to {c.after}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Details / Rationale from Backend */}
              {ad.details && (
                <p className="text-xs text-slate-300 bg-slate-900/50 rounded-lg p-2 border border-slate-800/60 leading-relaxed break-words">
                  {ad.details}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
