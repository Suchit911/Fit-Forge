import React from 'react'
import { AlertTriangle, Sliders, RefreshCw } from 'lucide-react'
import type { WorkoutPlanResponse } from '../../../types/workoutPlan'

interface PlanDiagnosticsAlertProps {
  plan: WorkoutPlanResponse
  onReconfigure: () => void
}

export const PlanDiagnosticsAlert: React.FC<PlanDiagnosticsAlertProps> = ({ plan, onReconfigure }) => {
  const isConflict = plan.conflicting_filters && plan.conflicting_filters.length > 0
  const isShortfall = plan.title === 'Catalog Shortfall' || plan.diagnostics?.some((d) => d.includes('shortfall') || d.includes('short of'))

  let stateTitle = 'Plan Configuration Incomplete'
  let stateMessage = 'The planner could not generate a feasible routine with the current parameters.'
  let advice = 'Review your constraints and try adjusting equipment or duration.'

  if (isConflict) {
    stateTitle = 'Conflicting Constraints Detected (State C)'
    stateMessage = 'Your selected filters contain mutually exclusive requirements that prevent exercise allocation.'
    advice = 'Try removing an exclusion or broadening your available equipment selection.'
  } else if (isShortfall) {
    stateTitle = 'Catalog Exercise Shortfall (State D)'
    stateMessage = 'There are not enough catalog exercises matching all selected filters to fill every required workout slot.'
    advice = 'Broaden your equipment selection, change environment to Gym, or remove movement pattern/exercise exclusions.'
  } else if (!plan.feasibility_check_passed) {
    stateTitle = 'Invalid Input Parameters (State B)'
    stateMessage = 'One or more required parameters cannot be satisfied by the planning engine.'
    advice = 'Ensure at least one equipment type is selected (e.g. Bodyweight or Dumbbells) and verify training days.'
  }

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 text-left space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base font-bold text-amber-200">{stateTitle}</h3>
          <p className="text-xs text-amber-300/90 mt-1">{stateMessage}</p>
        </div>
      </div>

      {plan.conflicting_filters && plan.conflicting_filters.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-slate-900/60 p-3 space-y-1.5">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-400">
            Detected Conflicting Filters:
          </span>
          <ul className="list-disc list-inside text-xs text-slate-300 space-y-0.5">
            {plan.conflicting_filters.map((filter, idx) => (
              <li key={idx} className="font-mono text-[11px] text-amber-200">
                {filter}
              </li>
            ))}
          </ul>
        </div>
      )}

      {plan.diagnostics && plan.diagnostics.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-slate-900/60 p-3 space-y-1.5">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400">
            Planner Diagnostics:
          </span>
          <ul className="list-disc list-inside text-xs text-slate-300 space-y-0.5">
            {plan.diagnostics.map((diag, idx) => (
              <li key={idx} className="text-xs text-slate-300">
                {diag}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2 border-t border-amber-500/20">
        <p className="text-xs text-slate-400 flex items-center gap-1.5">
          <Sliders className="h-3.5 w-3.5 text-amber-400" />
          <span>{advice}</span>
        </p>
        <button
          type="button"
          onClick={onReconfigure}
          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 px-4 py-2 text-xs font-bold transition-all cursor-pointer shadow-md shadow-amber-500/20 shrink-0"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Reconfigure Plan
        </button>
      </div>
    </div>
  )
}
