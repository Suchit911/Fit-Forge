import React from 'react'
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts'
import type { FormBreakdownItem } from '../../types'

export interface FormScoreBreakdownCardProps {
  breakdown: FormBreakdownItem[]
}

export const FormScoreBreakdownCard: React.FC<FormScoreBreakdownCardProps> = ({ breakdown = [] }) => {
  const hasScores = breakdown.length > 0 && breakdown.some((b) => b.score > 0)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Form Score Breakdown
      </h3>

      {!hasScores ? (
        <div className="h-48 w-full flex flex-col items-center justify-center p-4 text-center space-y-1 text-slate-500 font-mono text-xs">
          <p>No breakdown data yet.</p>
          <p className="text-[11px] text-slate-600">Scores will compute automatically after completed repetitions.</p>
        </div>
      ) : (
        <div className="h-48 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={breakdown} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 10 }} />
              <Radar
                name="Form Score"
                dataKey="score"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.4}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
