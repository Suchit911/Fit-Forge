import React from 'react'
import { Sparkles, ArrowRight, ShieldCheck, History, AlertCircle } from 'lucide-react'
import { Modal } from '../ui/Modal.tsx'
import { Badge } from '../ui/Badge.tsx'
import { Skeleton } from '../ui/Skeleton.tsx'
import { useProgramVersions } from '../../hooks/useActiveProgram.ts'
import type { ProgramResponse, AdaptationAuditRecord } from '../../types/program.ts'
import {
  formatAdaptationType,
  formatRuleCode,
  formatAdaptationDate,
  extractMetricComparisons,
  formatExerciseDisplayName,
  formatAffectedDays,
} from '../../utils/adaptationFormatting.ts'

export interface AdaptationHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  program?: ProgramResponse | null
}

export const AdaptationHistoryModal: React.FC<AdaptationHistoryModalProps> = ({
  isOpen,
  onClose,
  program,
}) => {
  // Query authoritative version and adaptation history from backend
  const { versions, isLoading, isError } = useProgramVersions({ enabled: isOpen })

  // Use versions.adaptationHistory if available, otherwise program.adaptationHistory
  const records: AdaptationAuditRecord[] =
    (versions?.adaptationHistory ?? versions?.adaptation_history ?? program?.adaptationHistory ?? program?.adaptation_history ?? []) as AdaptationAuditRecord[]

  const currentPlanVersion = versions?.planVersion ?? versions?.plan_version ?? program?.planVersion ?? 1
  const totalApplied = versions?.totalAdaptationsApplied ?? versions?.total_adaptations_applied ?? records.length

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Adaptation History"
      description={`Authoritative record of adaptive updates applied to your mesocycle (Current: Plan v${currentPlanVersion})`}
      className="max-w-2xl"
    >
      <div className="space-y-4 text-left">
        {/* Loading State */}
        {isLoading && (
          <div className="space-y-3 py-2">
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
          </div>
        )}

        {/* Error State */}
        {!isLoading && isError && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-center space-y-2">
            <AlertCircle className="h-6 w-6 text-red-400 mx-auto" aria-hidden="true" />
            <p className="text-xs font-semibold text-red-300">
              Failed to load program versions from server.
            </p>
            <p className="text-[11px] text-slate-400">
              Showing cached adaptation records if available.
            </p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && records.length === 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-8 text-center space-y-3">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-slate-400 border border-slate-800">
              <History className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-slate-200">No adaptive updates yet.</h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                This is normal for a new program. As you log workouts and establish performance trends, the system evaluates progression opportunities.
              </p>
            </div>
          </div>
        )}

        {/* History Records List */}
        {!isLoading && records.length > 0 && (
          <div className="space-y-3 max-h-[60vh] overflow-y-auto overscroll-contain pr-1">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono pb-1 border-b border-slate-800/60">
              <span>{totalApplied} adaptation{totalApplied === 1 ? '' : 's'} recorded</span>
              <span>Active Plan v{currentPlanVersion}</span>
            </div>

            {records.map((rec, idx) => {
              const typeMeta = formatAdaptationType(rec.adaptationType || rec.adaptation_type)
              const ruleTitle = formatRuleCode(rec.ruleCode || rec.rule_code)
              const exName = formatExerciseDisplayName(rec.affectedExerciseId || rec.affected_exercise_id || rec.exerciseId || rec.exercise_id)
              const dateStr = formatAdaptationDate(rec.appliedAt || rec.applied_at)
              const comparisons = extractMetricComparisons(
                rec.previousPrescription || rec.previous_prescription,
                rec.appliedPrescription || rec.applied_prescription || rec.proposedPrescription || rec.proposed_prescription
              )
              const affectedStr = formatAffectedDays(rec.affectedDays || rec.affected_days)
              const vBefore = rec.versionBefore ?? rec.version_before
              const vAfter = rec.versionAfter ?? rec.version_after
              const decisionId = rec.decisionId || rec.decision_id

              return (
                <div
                  key={decisionId || idx}
                  className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-3 hover:border-slate-700 transition-colors"
                >
                  {/* Top Bar: Type, Version Transition, Date */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={typeMeta.badgeVariant}>
                        {typeMeta.label}
                      </Badge>
                      {vBefore !== undefined && vAfter !== undefined && (
                        <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-900 border border-slate-800 rounded-full px-2 py-0.5">
                          v{vBefore} → v{vAfter}
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      {dateStr}
                    </span>
                  </div>

                  {/* Exercise & Rule Header */}
                  <div className="min-w-0">
                    <h5 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-cyan-400 shrink-0" aria-hidden="true" />
                      <span className="break-words">{exName}</span>
                    </h5>
                    <p className="text-xs text-slate-400 mt-0.5 break-words">{ruleTitle}</p>
                  </div>

                  {/* Metric Comparisons (Before → After) */}
                  {comparisons.length > 0 && (
                    <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                      {comparisons.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-lg bg-slate-900/90 border border-slate-800/80 p-2 text-left"
                        >
                          <span className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                            {c.metric}
                          </span>
                          <div className="flex items-center gap-1.5 text-xs font-bold font-mono mt-0.5">
                            <span className="text-slate-400 line-through">{c.before}</span>
                            <ArrowRight className="h-3 w-3 text-slate-400 shrink-0" aria-hidden="true" />
                            <span className="text-emerald-400">{c.after}</span>
                            <span className="sr-only"> changed from {c.before} to {c.after}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Details / Rationale */}
                  {(rec.details || rec.rationale) && (
                    <p className="text-xs text-slate-300 bg-slate-900/40 rounded-lg p-2 border border-slate-800/40 leading-relaxed break-words">
                      {rec.details || rec.rationale}
                    </p>
                  )}

                  {/* Meta / Scope & Decision ID */}
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/40">
                    <div>
                      {affectedStr && <span>Scope: {affectedStr}</span>}
                    </div>
                    {decisionId && (
                      <div className="flex items-center gap-1">
                        <ShieldCheck className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                        <span title={decisionId}>ID: {decisionId.slice(0, 10)}...</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </Modal>
  )
}
