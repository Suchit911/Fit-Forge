import React from 'react'
import type { SuggestedQuestionItem } from '../../types'
import { Dumbbell, Utensils, Heart, Activity, FileText, ChevronRight } from 'lucide-react'

export interface SuggestedQuestionsSectionProps {
  questions: SuggestedQuestionItem[]
  onQuestionClick: (q: string) => void
}

export const SuggestedQuestionsSection: React.FC<SuggestedQuestionsSectionProps> = ({
  questions,
  onQuestionClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'dumbbell':
        return <Dumbbell className="h-4 w-4" />
      case 'utensils':
        return <Utensils className="h-4 w-4" />
      case 'heart':
        return <Heart className="h-4 w-4" />
      case 'activity':
        return <Activity className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-3 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Suggested Questions</h3>

      <div className="relative">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {questions.map((q) => (
            <button
              key={q.id}
              type="button"
              onClick={() => onQuestionClick(q.question)}
              className="group rounded-2xl border border-slate-800 bg-slate-900/90 p-4 text-left space-y-3 transition-all hover:border-emerald-500/50 hover:bg-slate-900 cursor-pointer flex flex-col justify-between"
            >
              <div
                className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-800 bg-slate-950 shrink-0"
                style={{ color: q.color }}
              >
                {getIcon(q.iconName)}
              </div>

              <p className="text-xs font-bold text-slate-200 group-hover:text-emerald-400 transition-colors leading-relaxed">
                {q.question}
              </p>
            </button>
          ))}
        </div>

        {/* Carousel Chevron Arrow Right */}
        <button
          type="button"
          aria-label="Next questions"
          className="absolute -right-3 top-1/2 -translate-y-1/2 hidden lg:flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
