import React, { useState } from 'react'
import { AlertCircle, RotateCcw } from 'lucide-react'
import { useGenerateWorkoutPlan } from '../../../hooks/useWorkoutPlan'
import { PlanGenerationForm } from './PlanGenerationForm'
import { GeneratedWorkoutPlanView } from './GeneratedWorkoutPlanView'
import { PlanDiagnosticsAlert } from './PlanDiagnosticsAlert'
import type { WorkoutPlanGenerateRequest, WorkoutPlanResponse } from '../../../types/workoutPlan'

export const WorkoutPlanGenerator: React.FC = () => {
  const { generatePlan, isGenerating, error, reset } = useGenerateWorkoutPlan()
  const [activePlan, setActivePlan] = useState<WorkoutPlanResponse | null>(null)
  const [lastRequest, setLastRequest] = useState<WorkoutPlanGenerateRequest | undefined>(undefined)

  const handleGenerate = async (request: WorkoutPlanGenerateRequest) => {
    setLastRequest(request)
    try {
      const response = await generatePlan(request)
      setActivePlan(response)
    } catch {
      // Error handled by TanStack mutation error state
    }
  }

  const handleReconfigure = () => {
    setActivePlan(null)
    reset()
  }

  return (
    <div className="space-y-6">
      {/* Network or Server HTTP Error Banner */}
      {error && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-5 text-left flex items-start gap-3">
          <div className="p-2 rounded-xl bg-red-500/20 text-red-400 shrink-0">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-red-200">Plan Generation Error</h3>
            <p className="text-xs text-red-300/90 leading-relaxed">{error.message}</p>
            <button
              type="button"
              onClick={handleReconfigure}
              className="mt-2 text-xs font-bold text-red-400 hover:text-red-300 underline inline-flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="h-3 w-3" /> Try again with different parameters
            </button>
          </div>
        </div>
      )}

      {/* Render based on state: Diagnostic Shortfall vs Generated Plan vs Form */}
      {activePlan ? (
        activePlan.feasibility_check_passed ? (
          <GeneratedWorkoutPlanView plan={activePlan} onReconfigure={handleReconfigure} />
        ) : (
          <PlanDiagnosticsAlert plan={activePlan} onReconfigure={handleReconfigure} />
        )
      ) : (
        <PlanGenerationForm
          onSubmit={handleGenerate}
          isGenerating={isGenerating}
          initialValues={lastRequest}
        />
      )}
    </div>
  )
}
