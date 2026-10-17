import React from 'react'
import type { CalorieFlowEntry } from '../../types'
import { ResponsiveContainer, LineChart, Line } from 'recharts'

export interface CalorieFlowCardProps {
  flow: CalorieFlowEntry[]
}

export const CalorieFlowCard: React.FC<CalorieFlowCardProps> = ({ flow }) => {
  // Compute chart points for line graph
  let running = flow.length > 0 ? flow[0].amount : 0
  const chartData = flow.map((item, i) => {
    if (i === 0) running = item.amount
    else running += item.amount
    return { i, val: running }
  })

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Calorie Flow</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View Analytics
        </button>
      </div>

      <div className="relative pt-1">
        {/* Line Chart Visual Backdrop */}
        <div className="h-10 w-full mb-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <Line type="monotone" dataKey="val" stroke="#10b981" strokeWidth={2} strokeDasharray="3 3" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Step Flow Columns */}
        <div className="grid grid-cols-7 gap-1 font-mono text-center border-t border-slate-800/60 pt-2">
          {flow.map((entry, idx) => {
            const isGoal = entry.type === 'goal'
            const isRem = entry.type === 'remaining'

            const textColor = isGoal
              ? 'text-slate-300'
              : isRem
              ? 'text-emerald-400 font-extrabold'
              : 'text-rose-400'

            return (
              <div key={idx} className="space-y-1">
                <span className={`text-xs font-bold block ${textColor}`}>
                  {isGoal ? entry.amount.toLocaleString() : isRem ? entry.amount : entry.amount}
                </span>
                <span className="text-[9px] text-slate-400 block truncate">{entry.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
