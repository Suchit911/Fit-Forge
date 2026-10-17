import React from 'react'
import { Dumbbell, Repeat, Zap, Clock } from 'lucide-react'

export interface ExerciseAnalysisSummaryProps {
  exerciseName: string
  setInfo: string
  weightKg: number
  reps: number
  rpe: number
  restTime: string
  formScore: number | null
  formStatus: string
  analysisTime: string
  confidence: string
  image: string
}

export const ExerciseAnalysisSummary: React.FC<ExerciseAnalysisSummaryProps> = ({
  exerciseName,
  setInfo,
  weightKg,
  reps,
  rpe,
  restTime,
  formScore,
  formStatus,
  analysisTime,
  confidence,
  image,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 flex flex-col md:flex-row md:items-center justify-between gap-6 text-left shadow-2xl">
      
      {/* Left Thumbnail & Info */}
      <div className="flex items-center gap-4">
        <div className="h-16 w-24 rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
          <img src={image} alt={exerciseName} className="w-full h-full object-cover opacity-85" />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-slate-100 tracking-tight">{exerciseName}</h2>
            <span className="rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-mono font-bold">
              {setInfo}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-300">
            <span className="flex items-center gap-1">
              <Dumbbell className="h-3.5 w-3.5 text-emerald-400" /> {weightKg} kg
            </span>
            <span className="flex items-center gap-1">
              <Repeat className="h-3.5 w-3.5 text-emerald-400" /> {reps} Reps
            </span>
            <span className="flex items-center gap-1">
              <Zap className="h-3.5 w-3.5 text-amber-400" /> RPE {rpe}
            </span>
            <span className="flex items-center gap-1 text-slate-400">
              <Clock className="h-3.5 w-3.5 text-slate-500" /> {restTime}
            </span>
          </div>
        </div>
      </div>

      {/* Right Form Score Ring, Analysis Time & Confidence */}
      <div className="flex items-center gap-8 border-t md:border-t-0 md:border-l border-slate-800/80 pt-4 md:pt-0 md:pl-8">
        
        {/* Form Score Ring */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-slate-400 font-mono uppercase">Form Score</span>
            <span className="text-xs font-bold text-emerald-400 font-mono">{formStatus}</span>
          </div>
          <div className="relative flex items-center justify-center">
            <svg className="h-16 w-16 transform -rotate-90">
              <circle cx="32" cy="32" r="26" stroke="#1e293b" strokeWidth="5" fill="transparent" />
              {formScore !== null && formScore > 0 && (
                <circle
                  cx="32"
                  cy="32"
                  r="26"
                  stroke="#10b981"
                  strokeWidth="5"
                  strokeDasharray="163"
                  strokeDashoffset={Math.max(0, 163 - (163 * Math.min(100, formScore)) / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              )}
            </svg>
            <span className="absolute text-sm font-extrabold text-slate-100 font-mono">
              {formScore !== null && formScore > 0 ? `${Math.round(formScore)}%` : '--'}
            </span>
          </div>
        </div>

        {/* Analysis Time */}
        <div className="text-center font-mono">
          <span className="text-[10px] text-slate-400 uppercase block">Analysis Time</span>
          <span className="text-base font-extrabold text-slate-100 block">{analysisTime}</span>
        </div>

        {/* Confidence */}
        <div className="text-center font-mono">
          <span className="text-[10px] text-slate-400 uppercase block">Confidence</span>
          <span className="text-xs font-extrabold text-emerald-400 block">{confidence}</span>
        </div>

      </div>

    </div>
  )
}
