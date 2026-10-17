import React from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import { useProgress } from '../../hooks'

export const ProgressOverviewCard: React.FC = () => {
  const { progress } = useProgress()

  const data = progress?.weightHistory || []

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left flex flex-col justify-between space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div>
          <h3 className="text-sm font-extrabold text-slate-100">Progress Overview</h3>
          <span className="text-[10px] text-slate-400 font-mono">Weight Trend (kg)</span>
        </div>
        <Link
          to="/progress"
          className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          See All
        </Link>
      </div>

      {data.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-8 text-center space-y-2 rounded-xl bg-slate-950/40 border border-slate-800/60 my-auto">
          <TrendingUp className="h-7 w-7 text-slate-600" />
          <p className="text-xs font-bold text-slate-300">No Weight History Recorded Yet</p>
          <p className="text-[10px] text-slate-500 max-w-xs">
            Log your body weight entries in the Progress section to visualize trends over time.
          </p>
        </div>
      ) : (
        /* Recharts Weight Trend Graph */
        <div className="h-44 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis
                dataKey="date"
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                fontFamily="monospace"
              />
              <YAxis
                domain={['dataMin - 2', 'dataMax + 2']}
                stroke="#64748b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                fontFamily="monospace"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#1e293b',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: '#f8fafc',
                  fontFamily: 'monospace',
                }}
                formatter={(value: any) => [`${value} kg`, 'Weight']}
              />
              <Line
                type="monotone"
                dataKey="weightKg"
                stroke="#10b981"
                strokeWidth={3}
                dot={{ r: 4, fill: '#10b981', stroke: '#0f172a', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#10b981', stroke: '#f8fafc', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

    </div>
  )
}
