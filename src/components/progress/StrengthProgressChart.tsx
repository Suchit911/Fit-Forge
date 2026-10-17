import React from 'react'
import type { StrengthProgressPoint } from '../../types'
import { Info, ChevronDown, Maximize2 } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

export interface StrengthProgressChartProps {
  data: StrengthProgressPoint[]
}

export const StrengthProgressChart: React.FC<StrengthProgressChartProps> = ({ data }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      {/* Top Header & Dropdowns */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-extrabold text-slate-100">Strength Progress Over Time</h3>
          <Info className="h-3.5 w-3.5 text-slate-500 cursor-pointer" />
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-slate-300">
            <span>All Exercises</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          </div>

          <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-slate-300">
            <span>1M</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          </div>

          <button type="button" aria-label="Fullscreen" className="p-1 text-slate-400 hover:text-slate-200">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Legend & Hover Tooltip Overlay */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
        <div className="md:col-span-8 space-y-3">
          <div className="flex items-center gap-6 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
              <span className="h-2 w-2 rounded-full bg-emerald-400" /> Upper Body (kg)
            </span>
            <span className="flex items-center gap-1.5 text-blue-400 font-bold">
              <span className="h-2 w-2 rounded-full bg-blue-400" /> Lower Body (kg)
            </span>
            <span className="flex items-center gap-1.5 text-purple-400 font-bold">
              <span className="h-2 w-2 rounded-full bg-purple-400" /> Total Volume (kg)
            </span>
          </div>

          {/* Line Chart */}
          <div className="h-60 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis
                  stroke="#64748b"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  tickFormatter={(v) => `${v / 1000}K`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '12px' }}
                />
                <Line type="monotone" dataKey="upperBodyKg" stroke="#10b981" strokeWidth={2.5} dot={{ fill: '#10b981', r: 4 }} />
                <Line type="monotone" dataKey="lowerBodyKg" stroke="#3b82f6" strokeWidth={2.5} dot={{ fill: '#3b82f6', r: 4 }} />
                <Line type="monotone" dataKey="totalVolumeKg" stroke="#a855f7" strokeWidth={2.5} dot={{ fill: '#a855f7', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Reference Tooltip Summary Box */}
        <div className="md:col-span-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 space-y-3 font-mono text-xs shadow-lg">
          <span className="text-[10px] text-slate-400 block border-b border-slate-800 pb-1.5">
            May 12, 2025
          </span>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Upper Body
              </span>
              <span className="font-extrabold text-slate-100">6,240 kg</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-blue-400 font-bold">
                <span className="h-2 w-2 rounded-full bg-blue-400" /> Lower Body
              </span>
              <span className="font-extrabold text-slate-100">4,580 kg</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-purple-400 font-bold">
                <span className="h-2 w-2 rounded-full bg-purple-400" /> Total Volume
              </span>
              <span className="font-extrabold text-slate-100">12,540 kg</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
