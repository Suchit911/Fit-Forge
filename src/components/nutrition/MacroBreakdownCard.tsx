import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

export interface MacroBreakdownCardProps {
  consumedCalories: number
  proteinGrams: number
  carbsGrams: number
  fatGrams: number
}

export const MacroBreakdownCard: React.FC<MacroBreakdownCardProps> = ({
  consumedCalories,
  proteinGrams,
  carbsGrams,
  fatGrams,
}) => {
  const data = [
    { name: 'Protein', value: proteinGrams * 4, grams: proteinGrams, pct: '31%', color: '#10b981' },
    { name: 'Carbs', value: carbsGrams * 4, grams: carbsGrams, pct: '41%', color: '#f59e0b' },
    { name: 'Fat', value: fatGrams * 9, grams: fatGrams, pct: '30%', color: '#a855f7' },
  ]

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Macronutrient Breakdown
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
        {/* Donut Chart with Center Text */}
        <div className="sm:col-span-6 relative flex items-center justify-center h-36">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                innerRadius={40}
                outerRadius={56}
                paddingAngle={4}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="#0f172a" strokeWidth={2} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          <div className="absolute text-center">
            <span className="text-base font-extrabold text-slate-100 font-mono block leading-none">
              {consumedCalories.toLocaleString()}
            </span>
            <span className="text-[9px] text-slate-500 font-mono uppercase">Calories</span>
          </div>
        </div>

        {/* Macro Percentages & Grams Legend */}
        <div className="sm:col-span-6 space-y-2 font-mono text-xs">
          {data.map((m) => (
            <div key={m.name} className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-slate-300 text-[11px]">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: m.color }} />
                <span className="font-bold">{m.name}</span>
              </span>
              <div className="text-right">
                <span className="text-slate-400 font-bold block text-[11px]">{m.pct}</span>
                <span className="text-[9px] text-slate-500 block">{m.grams}g</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
