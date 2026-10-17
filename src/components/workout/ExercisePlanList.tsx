import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Clock } from 'lucide-react'
import type { WorkoutExercise } from '../../types'

export interface ExerciseItemData {
  id: string
  number: string
  name: string
  target: string
  sets: string
  reps: string
  rest: string
  equipment: string
  image: string
  description?: string
  instructions?: string[]
}

export interface ExercisePlanListProps {
  exercises?: WorkoutExercise[]
}

export const ExercisePlanList: React.FC<ExercisePlanListProps> = ({ exercises = [] }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const displayExercises: ExerciseItemData[] = exercises.map((we, idx) => ({
    id: we.exerciseId || `ex_${idx}`,
    number: String(idx + 1).padStart(2, '0'),
    name: we.exercise?.name || 'Exercise',
    target: we.exercise?.primaryMuscles?.join(', ') || 'Full Body',
    sets: `${we.sets?.length || 3} sets`,
    reps: `${we.sets?.[0]?.targetReps || 10} reps`,
    rest: `${we.restSecondsBetweenSets || 90} sec`,
    equipment: we.exercise?.equipment?.join(', ') || 'Bodyweight',
    image: idx % 2 === 0 ? '/assets/dashboard_push_lifter.jpg' : '/assets/workout_lower_body.jpg',
    description: we.exercise?.description || '',
    instructions: we.exercise?.instructions || [],
  }))

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  if (displayExercises.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400 bg-slate-900/30">
        No exercise plan details recorded for this routine.
      </div>
    )
  }

  return (
    <div className="space-y-4 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Exercise Plan</h3>

      <div className="space-y-2.5">
        {displayExercises.map((ex) => {

          const isExpanded = expandedId === ex.id

          return (
            <div
              key={ex.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/90 overflow-hidden transition-all hover:border-slate-700"
            >
              {/* Main Row */}
              <div
                onClick={() => toggleExpand(ex.id)}
                className="flex items-center justify-between p-3.5 cursor-pointer select-none"
              >
                {/* Left Sequence, Thumbnail & Title */}
                <div className="flex items-center gap-3 min-w-[200px]">
                  <span className="text-sm font-extrabold font-mono text-emerald-400">
                    {ex.number}
                  </span>
                  <div className="h-10 w-14 rounded-lg overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
                    <img src={ex.image} alt={ex.name} className="w-full h-full object-cover opacity-80" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-100">{ex.name}</h4>
                    <span className="text-[10px] text-slate-400">{ex.target}</span>
                  </div>
                </div>

                {/* Metadata Columns */}
                <div className="hidden sm:flex items-center gap-6 text-xs font-mono">
                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Sets</span>
                    <span className="font-semibold text-slate-200">{ex.sets}</span>
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Reps</span>
                    <span className="font-semibold text-slate-200">{ex.reps}</span>
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Rest</span>
                    <span className="font-semibold text-slate-300">{ex.rest}</span>
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Equipment</span>
                    <span className="font-semibold text-slate-300">{ex.equipment}</span>
                  </div>
                </div>

                {/* Expand Toggle Chevron */}
                <div className="text-slate-400 p-1">
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </div>
              </div>

              {/* Expandable Technique Details */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/60 text-xs text-slate-300 space-y-2">
                  <p>{ex.description}</p>
                  {ex.instructions && (
                    <ol className="list-decimal list-inside space-y-1 text-slate-400 text-[11px]">
                      {ex.instructions.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Rest Info Pill */}
      <div className="pt-2 flex items-center justify-center gap-1.5 text-xs text-slate-400 font-mono">
        <Clock className="h-3.5 w-3.5 text-slate-500" />
        <span>Rest 2–3 min between exercises</span>
      </div>
    </div>
  )
}
