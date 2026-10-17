import React from 'react'
import type { AICoachSettingsData } from '../../types'
import { Bot, Smile, Zap, Target, Dumbbell, Apple, Eye, RotateCcw } from 'lucide-react'

export interface AICoachSettingsCardProps {
  aiCoach: AICoachSettingsData
  onUpdate: (data: Partial<AICoachSettingsData>) => void
  onReset: () => void
}

export const AICoachSettingsCard: React.FC<AICoachSettingsCardProps> = ({ aiCoach, onUpdate, onReset }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Bot className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-100">AI Coach Settings</h3>
        </div>

        <div className="space-y-2.5 font-mono text-xs">
          {/* Coach Personality */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Smile className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Coach Personality</span>
            </div>
            <select
              value={aiCoach.personality}
              onChange={(e) => onUpdate({ personality: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Motivational">Motivational</option>
              <option value="Strict & Disciplined">Strict & Disciplined</option>
              <option value="Scientific">Scientific</option>
            </select>
          </div>

          {/* Coaching Intensity */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Coaching Intensity</span>
            </div>
            <select
              value={aiCoach.intensity}
              onChange={(e) => onUpdate({ intensity: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Moderate">Moderate</option>
              <option value="High">High</option>
              <option value="Extreme">Extreme</option>
            </select>
          </div>

          {/* Primary Focus */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Primary Focus</span>
            </div>
            <select
              value={aiCoach.focus}
              onChange={(e) => onUpdate({ focus: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Muscle Gain">Muscle Gain</option>
              <option value="Fat Loss">Fat Loss</option>
              <option value="Strength">Strength</option>
            </select>
          </div>

          {/* Workout Recommendations */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Dumbbell className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Workout Recommendations</span>
            </div>
            <select
              value={aiCoach.workoutRecommendations}
              onChange={(e) => onUpdate({ workoutRecommendations: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Standard">Standard</option>
              <option value="Advanced">Advanced</option>
              <option value="Custom">Custom</option>
            </select>
          </div>

          {/* Nutrition Recommendations */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Apple className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Nutrition Recommendations</span>
            </div>
            <select
              value={aiCoach.nutritionRecommendations}
              onChange={(e) => onUpdate({ nutritionRecommendations: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Basic">Basic</option>
              <option value="Personalized">Personalized</option>
            </select>
          </div>

          {/* Form Analysis Insights */}
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Form Analysis Insights</span>
            </div>
            <select
              value={aiCoach.formAnalysisInsights}
              onChange={(e) => onUpdate({ formAnalysisInsights: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Standard">Standard</option>
              <option value="Detailed">Detailed</option>
            </select>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1.5 text-xs font-mono text-purple-400 hover:text-purple-300 font-bold transition-colors cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset to Default
        </button>
      </div>
    </div>
  )
}
