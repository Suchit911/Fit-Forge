import React, { useState } from 'react'
import {
  Dumbbell,
  Calendar,
  Clock,
  Target,
  Home,
  Check,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RotateCcw,
} from 'lucide-react'
import type {
  WorkoutPlanGenerateRequest,
  FitnessGoal,
  EnvironmentType,
  EquipmentType,
  WorkoutSplitType,
} from '../../../types/workoutPlan'

interface PlanGenerationFormProps {
  onSubmit: (request: WorkoutPlanGenerateRequest) => void
  isGenerating: boolean
  initialValues?: WorkoutPlanGenerateRequest
}

const GOALS: { id: FitnessGoal; label: string; desc: string }[] = [
  { id: 'muscle_gain', label: 'Muscle Gain', desc: 'Maximize hypertrophy & metabolic volume' },
  { id: 'strength', label: 'Strength', desc: 'Focus on multi-joint compound force production' },
  { id: 'fat_loss', label: 'Fat Loss', desc: 'High density conditioning with preserved lean mass' },
  { id: 'endurance', label: 'Endurance', desc: 'Sustained work capacity & high repetition ranges' },
  { id: 'general_fitness', label: 'General Fitness', desc: 'Balanced functional mobility and full-body health' },
]

const ENVIRONMENTS: { id: EnvironmentType; label: string }[] = [
  { id: 'gym', label: 'Commercial Gym' },
  { id: 'home', label: 'Home Gym' },
  { id: 'outdoor', label: 'Outdoor' },
]

const EQUIPMENT_OPTIONS: { id: EquipmentType; label: string }[] = [
  { id: 'bodyweight', label: 'Bodyweight' },
  { id: 'dumbbells', label: 'Dumbbells' },
  { id: 'barbell', label: 'Barbell' },
  { id: 'bench', label: 'Flat Bench' },
  { id: 'incline_bench', label: 'Incline Bench' },
  { id: 'cable_machine', label: 'Cable Machine' },
  { id: 'smith_machine', label: 'Smith Machine' },
  { id: 'leg_press', label: 'Leg Press' },
  { id: 'pull_up_bar', label: 'Pull-up Bar' },
  { id: 'dip_station', label: 'Dip Station' },
  { id: 'resistance_bands', label: 'Resistance Bands' },
  { id: 'kettlebell', label: 'Kettlebell' },
  { id: 'trap_bar', label: 'Trap Bar' },
]

export const PlanGenerationForm: React.FC<PlanGenerationFormProps> = ({
  onSubmit,
  isGenerating,
  initialValues,
}) => {
  const [trainingDays, setTrainingDays] = useState<number>(initialValues?.training_days_per_week ?? 4)
  const [planWeeks, setPlanWeeks] = useState<number>(initialValues?.plan_duration_weeks ?? 4)
  const [targetDuration, setTargetDuration] = useState<number>(initialValues?.target_workout_duration_minutes ?? 45)
  const [goal, setGoal] = useState<FitnessGoal>(initialValues?.target_goal ?? 'muscle_gain')
  const [environment, setEnvironment] = useState<EnvironmentType>(initialValues?.environment ?? 'gym')
  const [equipment, setEquipment] = useState<EquipmentType[]>(
    initialValues?.available_equipment ?? ['bodyweight', 'dumbbells', 'barbell', 'bench']
  )
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false)
  const [preferredSplit, setPreferredSplit] = useState<WorkoutSplitType | undefined>(
    initialValues?.preferred_split ?? undefined
  )
  const [formAnalysisOnly, setFormAnalysisOnly] = useState<boolean>(
    initialValues?.form_analysis_supported_only ?? false
  )

  const [validationError, setValidationError] = useState<string | null>(null)

  const toggleEquipment = (eq: EquipmentType) => {
    if (equipment.includes(eq)) {
      setEquipment(equipment.filter((item) => item !== eq))
    } else {
      setEquipment([...equipment, eq])
    }
  }

  const applyEquipmentPreset = (preset: 'gym' | 'home' | 'bodyweight') => {
    if (preset === 'gym') {
      setEquipment(['bodyweight', 'dumbbells', 'barbell', 'bench', 'cable_machine', 'smith_machine', 'pull_up_bar'])
      setEnvironment('gym')
    } else if (preset === 'home') {
      setEquipment(['bodyweight', 'dumbbells', 'bench'])
      setEnvironment('home')
    } else {
      setEquipment(['bodyweight'])
      setEnvironment('home')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)

    // Client-side UX validation
    if (trainingDays < 1 || trainingDays > 6) {
      setValidationError('Training days must be between 1 and 6 days per week.')
      return
    }
    if (planWeeks < 1 || planWeeks > 12) {
      setValidationError('Plan duration must be between 1 and 12 weeks.')
      return
    }
    if (targetDuration < 20 || targetDuration > 90) {
      setValidationError('Target duration must be between 20 and 90 minutes.')
      return
    }
    if (equipment.length === 0) {
      setValidationError('Please select at least one available equipment option (e.g. Bodyweight).')
      return
    }

    const payload: WorkoutPlanGenerateRequest = {
      training_days_per_week: trainingDays,
      plan_duration_weeks: planWeeks,
      target_workout_duration_minutes: targetDuration,
      target_goal: goal,
      environment: environment,
      available_equipment: equipment,
      form_analysis_supported_only: formAnalysisOnly,
    }

    if (preferredSplit) {
      payload.preferred_split = preferredSplit
    }

    onSubmit(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 sm:p-8 text-left space-y-8 backdrop-blur-sm">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-2 text-emerald-400 font-extrabold text-xs tracking-wider uppercase">
          <Sparkles className="h-4 w-4" />
          <span>Deterministic Program Generator</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-black text-slate-100 mt-1">Configure Your Workout Plan</h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Set your schedule, goals, and equipment. The deterministic planning engine will build a tailored multi-week mesocycle with periodization and RPE progression.
        </p>
      </div>

      {validationError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs font-semibold text-red-300">
          {validationError}
        </div>
      )}

      {/* Primary Goal Selector */}
      <div className="space-y-3">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Target className="h-4 w-4 text-emerald-400" /> Primary Fitness Goal
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {GOALS.map((g) => {
            const isSelected = goal === g.id
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => setGoal(g.id)}
                className={`p-4 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-500/10 text-slate-100 shadow-md shadow-emerald-500/10'
                    : 'border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className={`text-sm font-bold ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}>
                    {g.label}
                  </span>
                  {isSelected && <Check className="h-4 w-4 text-emerald-400" />}
                </div>
                <span className="text-[11px] text-slate-400 mt-2 leading-relaxed">{g.desc}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Schedule & Duration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        {/* Training Days */}
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" /> Training Days / Week
          </label>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5, 6].map((day) => (
              <button
                key={day}
                type="button"
                onClick={() => setTrainingDays(day)}
                className={`flex-1 h-11 rounded-xl font-bold text-sm transition-all cursor-pointer ${
                  trainingDays === day
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'border border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                {day}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-slate-500">
            {trainingDays <= 3 ? 'Routes to Full Body split' : trainingDays <= 5 ? 'Routes to Upper / Lower split' : 'Routes to Push / Pull / Legs'}
          </p>
        </div>

        {/* Plan Duration Weeks */}
        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" /> Program Length (Weeks)
          </label>
          <div className="flex items-center gap-2">
            {[1, 4, 8, 12].map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setPlanWeeks(w)}
                className={`flex-1 h-11 rounded-xl font-bold text-xs transition-all cursor-pointer ${
                  planWeeks === w
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : 'border border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                {w} {w === 1 ? 'Wk' : 'Wks'}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-slate-500">
            {planWeeks >= 4 ? 'Includes Week 4 deload consolidation' : 'Single test microcycle'}
          </p>
        </div>

        {/* Target Workout Duration */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-400" /> Target Duration
            </label>
            <span className="text-xs font-mono font-bold text-emerald-400">{targetDuration} min</span>
          </div>
          <input
            type="range"
            min={20}
            max={90}
            step={5}
            value={targetDuration}
            onChange={(e) => setTargetDuration(parseInt(e.target.value, 10))}
            className="w-full accent-emerald-500 cursor-pointer h-2 bg-slate-800 rounded-lg appearance-none"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500">
            <span>20m (Quick)</span>
            <span>45m (Standard)</span>
            <span>90m (Extended)</span>
          </div>
        </div>
      </div>

      {/* Environment & Equipment Section */}
      <div className="space-y-4 pt-2 border-t border-slate-800/80">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Dumbbell className="h-4 w-4 text-emerald-400" /> Available Equipment
          </label>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 text-[11px]">Presets:</span>
            <button
              type="button"
              onClick={() => applyEquipmentPreset('gym')}
              className="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-800/60 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold cursor-pointer transition-colors"
            >
              Commercial Gym
            </button>
            <button
              type="button"
              onClick={() => applyEquipmentPreset('home')}
              className="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-800/60 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold cursor-pointer transition-colors"
            >
              Home Dumbbells
            </button>
            <button
              type="button"
              onClick={() => applyEquipmentPreset('bodyweight')}
              className="px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-800/60 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold cursor-pointer transition-colors"
            >
              Bodyweight
            </button>
          </div>
        </div>

        {/* Environment Selector */}
        <div className="flex items-center gap-2">
          {ENVIRONMENTS.map((env) => (
            <button
              key={env.id}
              type="button"
              onClick={() => setEnvironment(env.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                environment === env.id
                  ? 'border border-emerald-500 bg-emerald-500/10 text-emerald-300'
                  : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Home className="h-3 w-3" /> {env.label}
            </button>
          ))}
        </div>

        {/* Equipment Checkboxes */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 pt-1">
          {EQUIPMENT_OPTIONS.map((eq) => {
            const isChecked = equipment.includes(eq.id)
            return (
              <button
                key={eq.id}
                type="button"
                onClick={() => toggleEquipment(eq.id)}
                className={`px-3 py-2 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all cursor-pointer ${
                  isChecked
                    ? 'border-emerald-500/60 bg-emerald-500/10 text-slate-100 font-semibold'
                    : 'border-slate-800/80 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                }`}
              >
                <span className="truncate">{eq.label}</span>
                <span
                  className={`h-4 w-4 rounded-md border flex items-center justify-center shrink-0 ml-1.5 transition-colors ${
                    isChecked ? 'border-emerald-500 bg-emerald-500 text-slate-950' : 'border-slate-700 bg-slate-800'
                  }`}
                >
                  {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Advanced Settings Accordion */}
      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          <span>Advanced Preferences & Overrides</span>
        </button>

        {showAdvanced && (
          <div className="mt-4 p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
            {/* Preferred Split Override */}
            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-300">
                Split Override (Optional — leave unset for automatic routing based on days):
              </label>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: undefined, label: 'Auto (Recommended)' },
                  { id: 'full_body' as WorkoutSplitType, label: 'Full Body' },
                  { id: 'upper_lower' as WorkoutSplitType, label: 'Upper / Lower' },
                  { id: 'push_pull_legs' as WorkoutSplitType, label: 'Push / Pull / Legs' },
                ].map((splitOption) => {
                  const isSelected = preferredSplit === splitOption.id
                  return (
                    <button
                      key={splitOption.label}
                      type="button"
                      onClick={() => setPreferredSplit(splitOption.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-emerald-500 text-slate-950 font-bold'
                          : 'border border-slate-800 bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {splitOption.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Form Analysis Supported Only */}
            <div className="pt-2">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formAnalysisOnly}
                  onChange={(e) => setFormAnalysisOnly(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                />
                <span>Form-Analysis Supported Only (Prioritize exercises compatible with real-time camera tracking)</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Submission Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-800/80">
        <button
          type="button"
          onClick={() => {
            setTrainingDays(4)
            setPlanWeeks(4)
            setTargetDuration(45)
            setGoal('muscle_gain')
            setEnvironment('gym')
            setEquipment(['bodyweight', 'dumbbells', 'barbell', 'bench'])
            setPreferredSplit(undefined)
            setFormAnalysisOnly(false)
            setValidationError(null)
          }}
          disabled={isGenerating}
          className="w-full sm:w-auto px-4 py-3 rounded-xl border border-slate-800 bg-slate-800/50 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-2"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset Defaults
        </button>

        <button
          type="submit"
          disabled={isGenerating}
          className="w-full sm:w-auto px-6 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs tracking-wide uppercase transition-all shadow-lg shadow-emerald-500/20 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <svg className="animate-spin h-4 w-4 text-slate-950" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Generating Deterministic Plan...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Generate Plan</span>
            </>
          )}
        </button>
      </div>
    </form>
  )
}
