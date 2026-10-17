import React, { useState, useEffect } from 'react'
import { Check, Clock, Loader2 } from 'lucide-react'
import type { PlannedSet } from '../../types/workoutPlan'

export interface SetItem {
  setNumber: number
  reps: number | string
  targetRepsNum: number
  actualReps: number
  targetWeightKg?: number
  weightKg: number
  rpe: number
  status: 'completed' | 'current' | 'pending'
  restSeconds: number
}

export interface SetTrackerTableProps {
  exerciseId?: string
  prescribedSets?: PlannedSet[]
  recordedSets?: Array<{
    setNumber: number
    actualReps: number
    actualWeightKg: number
    rpe?: number
    isCompleted: boolean
  }>
  onRecordSet?: (setRecord: {
    exerciseId: string
    setNumber: number
    actualReps: number
    actualWeightKg: number
    rpe?: number
  }) => Promise<void> | void
  isRecording?: boolean
}

export const SetTrackerTable: React.FC<SetTrackerTableProps> = ({
  exerciseId = '',
  prescribedSets,
  recordedSets,
  onRecordSet,
  isRecording = false,
}) => {
  const [sets, setSets] = useState<SetItem[]>([])
  const [activeRestSeconds, setActiveRestSeconds] = useState(75)

  // Initialize rows when prescribedSets or exerciseId changes
  useEffect(() => {
    if (prescribedSets && prescribedSets.length > 0) {
      const mappedSets: SetItem[] = prescribedSets.map((ps, idx) => {
        const recorded = recordedSets?.find((r) => r.setNumber === ps.set_number)
        const isCompleted = !!recorded?.isCompleted

        let repDisplay: string | number = ps.target_reps
        if (ps.target_reps_min && ps.target_reps_max) {
          repDisplay = `${ps.target_reps_min}–${ps.target_reps_max}`
        }

        const isCurrent =
          !isCompleted &&
          (idx === 0 || !!recordedSets?.find((r) => r.setNumber === ps.set_number - 1)?.isCompleted)
        const status: 'completed' | 'current' | 'pending' = isCompleted
          ? 'completed'
          : isCurrent
          ? 'current'
          : 'pending'

        const targetWeight = (ps.target_weight_kg ?? ps.weight_kg) ?? undefined

        return {
          setNumber: ps.set_number,
          reps: repDisplay,
          targetRepsNum: ps.target_reps_min || ps.target_reps || 10,
          actualReps: recorded?.actualReps ?? (ps.target_reps_min || ps.target_reps || 10),
          targetWeightKg: targetWeight ?? undefined,
          weightKg: recorded?.actualWeightKg ?? (targetWeight ?? 0),
          rpe: recorded?.rpe ?? (ps.target_rpe || 8),
          status,
          restSeconds: ps.rest_seconds || 90,
        }
      })
      setSets(mappedSets)
    } else {
      setSets([])
    }
  }, [exerciseId, prescribedSets, recordedSets])

  useEffect(() => {
    const currentSet = sets.find((s) => s.status === 'current')
    if (currentSet && activeRestSeconds > 0) {
      const timer = setInterval(() => {
        setActiveRestSeconds((prev) => (prev > 0 ? prev - 1 : 0))
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [sets, activeRestSeconds])

  const formatRestTime = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const handleRepsChange = (setNum: number, newReps: number) => {
    setSets((prev) =>
      prev.map((s) => (s.setNumber === setNum ? { ...s, actualReps: Math.max(1, newReps) } : s))
    )
  }

  const handleWeightChange = (setNum: number, newWeight: number) => {
    setSets((prev) =>
      prev.map((s) => (s.setNumber === setNum ? { ...s, weightKg: Math.max(0, newWeight) } : s))
    )
  }

  const markSetComplete = async (setNum: number) => {
    const targetSet = sets.find((s) => s.setNumber === setNum)
    if (!targetSet) return

    setSets((prev) =>
      prev.map((s) => {
        if (s.setNumber === setNum) {
          return { ...s, status: 'completed' }
        }
        if (s.setNumber === setNum + 1 && s.status !== 'completed') {
          return { ...s, status: 'current' }
        }
        return s
      })
    )
    setActiveRestSeconds(targetSet.restSeconds || 90)

    if (onRecordSet) {
      await onRecordSet({
        exerciseId,
        setNumber: setNum,
        actualReps: targetSet.actualReps,
        actualWeightKg: targetSet.weightKg,
        rpe: targetSet.rpe,
      })
    }
  }

  const completedCount = sets.filter((s) => s.status === 'completed').length

  if (sets.length === 0) {
    return (
      <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/90 text-center">
        <p className="text-xs font-mono text-slate-500">No prescribed sets for this exercise.</p>
      </div>
    )
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <span className="text-xs font-mono font-bold text-slate-300">
          {completedCount} of {sets.length} Sets Completed
        </span>
        {isRecording && (
          <span className="flex items-center gap-1 text-[11px] font-mono text-cyan-400">
            <Loader2 className="h-3 w-3 animate-spin" /> Recording set...
          </span>
        )}
      </div>

      {/* Table Column Headers */}
      <div className="grid grid-cols-6 text-center text-[10px] font-mono text-slate-500 uppercase font-bold py-1">
        <div className="text-left pl-2">Set</div>
        <div>Target (Actual)</div>
        <div>Weight (kg)</div>
        <div>RPE</div>
        <div>Status</div>
        <div>Rest</div>
      </div>

      {/* Set Rows */}
      <div className="space-y-2 font-mono text-xs">
        {sets.map((s) => {
          const isCompleted = s.status === 'completed'
          const isCurrent = s.status === 'current'

          return (
            <div
              key={s.setNumber}
              onClick={() => markSetComplete(s.setNumber)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  markSetComplete(s.setNumber)
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`Set ${s.setNumber}: target ${s.reps} reps, weight ${s.weightKg} kg, status ${s.status}. Click to mark complete.`}
              className={`grid grid-cols-6 items-center text-center p-3 rounded-xl border transition-all cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                isCompleted
                  ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-400'
                  : isCurrent
                  ? 'bg-cyan-950/30 border-cyan-500/40 text-slate-100 shadow-md shadow-cyan-950/40'
                  : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700'
              }`}
            >
              {/* Set Circle Indicator */}
              <div className="flex items-center gap-2 text-left pl-1">
                <div
                  className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold border ${
                    isCompleted
                      ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
                      : isCurrent
                      ? 'border-cyan-500 bg-cyan-500/20 text-cyan-400'
                      : 'border-slate-800 text-slate-500'
                  }`}
                >
                  {s.setNumber}
                </div>
              </div>

              {/* Reps (Prescribed target label + editable actual reps) */}
              <div className="flex items-center justify-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                <span className="text-[10px] text-slate-400 font-medium">({s.reps})</span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={s.actualReps}
                  disabled={isCompleted}
                  onChange={(e) => handleRepsChange(s.setNumber, parseInt(e.target.value) || 1)}
                  aria-label={`Set ${s.setNumber} actual reps`}
                  className={`w-12 text-center rounded px-1 py-0.5 text-xs font-mono font-bold bg-slate-900 border focus:outline-none ${
                    isCompleted
                      ? 'border-emerald-500/40 text-emerald-300'
                      : 'border-slate-700 text-slate-100 focus:border-cyan-400'
                  }`}
                />
              </div>

              {/* Weight Input (kg) */}
              <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
                {s.targetWeightKg !== undefined && s.targetWeightKg > 0 && (
                  <span className="text-[9px] text-slate-400 font-medium" title={`Prescribed target: ${s.targetWeightKg} kg`}>
                    ({s.targetWeightKg})
                  </span>
                )}
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={s.weightKg === 0 ? '' : s.weightKg}
                  placeholder={s.targetWeightKg ? `${s.targetWeightKg}` : '0'}
                  disabled={isCompleted}
                  onChange={(e) => handleWeightChange(s.setNumber, parseFloat(e.target.value) || 0)}
                  aria-label={`Set ${s.setNumber} actual weight in kg`}
                  className={`w-16 text-center rounded px-1 py-0.5 text-xs font-mono font-bold bg-slate-900 border focus:outline-none ${
                    isCompleted
                      ? 'border-emerald-500/40 text-emerald-300'
                      : 'border-slate-700 text-slate-100 focus:border-cyan-400'
                  }`}
                />
              </div>

              {/* RPE */}
              <div className="text-slate-400 font-semibold">{s.rpe ? `@ ${s.rpe}` : '—'}</div>

              {/* Status */}
              <div className="flex items-center justify-center gap-1 font-bold">
                {isCompleted ? (
                  <span className="flex items-center gap-1 text-emerald-400">
                    <Check className="h-3.5 w-3.5" /> Completed
                  </span>
                ) : isCurrent ? (
                  <span className="flex items-center gap-1 text-cyan-400">
                    <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" /> Log Set
                  </span>
                ) : (
                  <span className="text-slate-500">Pending</span>
                )}
              </div>

              {/* Rest */}
              <div className="flex items-center justify-center gap-1 text-slate-300">
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                <span>{isCurrent ? formatRestTime(activeRestSeconds) : `${s.restSeconds}s`}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
