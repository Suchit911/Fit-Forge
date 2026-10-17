import React from 'react'
import type { KeyMetricItem } from '../../types'
import { ResponsiveContainer, LineChart, Line } from 'recharts'

export interface KeyMetricsGridProps {
  metrics: KeyMetricItem[]
}

export const KeyMetricsGrid: React.FC<KeyMetricsGridProps> = ({ metrics = [] }) => {
  return (
    <div className="space-y-3 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Key Metrics</h3>

      {metrics.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-center text-xs text-slate-500 font-mono">
          No live heuristic metrics available. Metrics populate dynamically as repetitions are performed.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {metrics.map((item, idx) => {
            const isAmber = item.name === 'Tempo' || item.status === 'Fair'
            const isPoor = item.status === 'Poor'
            const sparkColor = isPoor ? '#f43f5e' : isAmber ? '#f59e0b' : '#10b981'
            const chartData = (item.trendData || []).map((val, i) => ({ i, val }))

            return (
              <div
                key={idx}
                className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-2 flex flex-col justify-between"
              >
                <div>
                  <span className="text-[11px] font-bold text-slate-400 block truncate">{item.name}</span>
                  <div className="flex items-baseline gap-1.5 mt-1 font-mono">
                    <span className="text-xl font-extrabold text-slate-100 leading-none">
                      {item.score !== null && item.score > 0 ? `${item.score}%` : '--'}
                    </span>
                    <span
                      className={`text-[10px] font-semibold ${
                        isPoor ? 'text-rose-400' : isAmber ? 'text-amber-400' : 'text-emerald-400'
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>
                </div>

                {/* Sparkline Chart */}
                <div className="h-8 w-full">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <Line
                          type="monotone"
                          dataKey="val"
                          stroke={sparkColor}
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-[10px] text-slate-600 font-mono">
                      Awaiting data
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
