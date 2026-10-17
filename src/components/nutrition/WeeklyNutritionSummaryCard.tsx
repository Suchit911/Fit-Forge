import React from 'react'
import type { WeeklyNutritionDay } from '../../types'
import { ResponsiveContainer, LineChart, Line } from 'recharts'

export interface WeeklyNutritionSummaryCardProps {
  days: WeeklyNutritionDay[]
}

export const WeeklyNutritionSummaryCard: React.FC<WeeklyNutritionSummaryCardProps> = ({ days }) => {
  const loggedDays = days.filter((d) => d.calories > 0)
  const avgCalories = loggedDays.length > 0
    ? Math.round(loggedDays.reduce((acc, d) => acc + d.calories, 0) / loggedDays.length)
    : 0
  const avgPct = loggedDays.length > 0
    ? Math.round(loggedDays.reduce((acc, d) => acc + d.pct, 0) / loggedDays.length)
    : 0
  const sparkData = days.map((d) => ({ v: d.calories }))

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <h3 className="text-base font-extrabold text-slate-100">Weekly Nutrition Summary</h3>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* 7 Days Circular Rings Left (9 cols) */}
        <div className="lg:col-span-9 grid grid-cols-7 gap-2 text-center font-mono">
          {days.map((d) => {
            const hasData = d.pct > 0
            const strokeDash = 138
            const strokeOffset = strokeDash - (strokeDash * d.pct) / 100

            return (
              <div key={d.day} className="space-y-1">
                <span className="text-xs font-bold text-slate-400 block">{d.day}</span>

                <div className="relative flex items-center justify-center mx-auto my-1">
                  <svg className="h-14 w-14 transform -rotate-90">
                    <circle cx="28" cy="28" r="22" stroke="#1e293b" strokeWidth="4" fill="transparent" />
                    {hasData && (
                      <circle
                        cx="28"
                        cy="28"
                        r="22"
                        stroke="#10b981"
                        strokeWidth="4"
                        strokeDasharray={strokeDash}
                        strokeDashoffset={strokeOffset}
                        strokeLinecap="round"
                        fill="transparent"
                      />
                    )}
                  </svg>
                  <span className="absolute text-xs font-extrabold text-slate-100 font-mono">
                    {hasData ? `${d.pct}%` : '0%'}
                  </span>
                </div>

                <span className="text-[10px] text-slate-400 font-bold block">
                  {hasData ? `${d.calories.toLocaleString()}` : '--'}
                </span>
                <span className="text-[9px] text-slate-500 block">{hasData ? 'kcal' : ''}</span>
              </div>
            )
          })}
        </div>

        {/* Weekly Average Right (3 cols) */}
        <div className="lg:col-span-3 border-t lg:border-t-0 lg:border-l border-slate-800/80 pt-4 lg:pt-0 lg:pl-6 space-y-2 font-mono text-left">
          <span className="text-xs font-bold text-slate-400 block uppercase">Weekly Average</span>

          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-emerald-400">{avgPct}%</span>
            <span className="text-xs text-slate-300 font-bold">
              {avgCalories > 0 ? `${avgCalories.toLocaleString()} kcal / day` : 'No logs yet'}
            </span>
          </div>

          {/* Green Sparkline */}
          <div className="h-8 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkData}>
                <Line type="monotone" dataKey="v" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
