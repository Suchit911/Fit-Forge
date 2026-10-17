import React from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'

export interface FormAnalysisBreadcrumbProps {
  exerciseTitle: string
}

export const FormAnalysisBreadcrumb: React.FC<FormAnalysisBreadcrumbProps> = ({ exerciseTitle }) => {
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-slate-400 text-left">
      <Link
        to="/exercises/ex_bench_press"
        className="inline-flex items-center gap-1 hover:text-emerald-400 transition-colors"
      >
        <ChevronLeft className="h-3.5 w-3.5" /> Back to Exercise Details
      </Link>
      <span className="text-slate-600">/</span>
      <span className="text-slate-200 font-bold">{exerciseTitle}</span>
    </div>
  )
}
