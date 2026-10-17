import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

export const DifficultyDonutCard: React.FC = () => {
  const data = [
    { name: 'Beginner', value: 156, pct: '30%', color: '#10b981' },
    { name: 'Intermediate', value: 256, pct: '50%', color: '#06b6d4' },
    { name: 'Advanced', value: 80, pct: '16%', color: '#f97316' },
    { name: 'Expert', value: 20, pct: '4%', color: '#ef4444' },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Difficulty Levels</h3>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
        {/* Donut Chart */}
        <div className="sm:col-span-6 relative flex items-center justify-center h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                innerRadius={36}
                outerRadius={50}
                paddingAngle={3}
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
              512
            </span>
            <span className="text-[9px] text-slate-500 font-mono uppercase">Total</span>
          </div>
        </div>

        {/* Legend */}
        <div className="sm:col-span-6 space-y-1.5 text-xs font-mono">
          {data.map((item) => (
            <div key={item.name} className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-300 text-[11px]">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                {item.name}
              </span>
              <span className="text-[10px] text-slate-400 font-bold">
                {item.value} <span className="text-slate-500">({item.pct})</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
