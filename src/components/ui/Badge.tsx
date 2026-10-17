import React from 'react'
import { cn } from '../../lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'emerald' | 'amber' | 'cyan' | 'red' | 'slate' | 'indigo'
}

export const Badge = ({ className, variant = 'slate', ...props }: BadgeProps) => {
  const variants = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    slate: 'bg-slate-800 text-slate-300 border-slate-700',
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variants[variant],
        className
      )}
      {...props}
    />
  )
}
