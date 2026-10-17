import React from 'react'
import type { PersonalRecordItem } from '../../types'
import { Dumbbell, ArrowUp } from 'lucide-react'

export interface PersonalRecordsCardProps {
  records: PersonalRecordItem[]
}

export const PersonalRecordsCard: React.FC<PersonalRecordsCardProps> = ({ records }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Personal Records</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {records.map((pr) => (
          <div
            key={pr.id}
            className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors group cursor-pointer"
          >
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                <Dumbbell className="h-4 w-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                  {pr.exerciseName}
                </h4>
                <span className="text-[10px] text-slate-400 block">{pr.date}</span>
              </div>
            </div>

            <div className="text-right space-y-0.5">
              <span className="text-xs font-extrabold text-slate-100 block">{pr.value}</span>
              <span className="text-[10px] font-bold text-emerald-400 flex items-center justify-end">
                {pr.improvement} <ArrowUp className="h-3 w-3 ml-0.5" />
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
