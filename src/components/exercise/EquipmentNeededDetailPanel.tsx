import React from 'react'
import { Dumbbell, Box } from 'lucide-react'

export interface EquipmentNeededDetailPanelProps {
  equipment?: string[]
}

export const EquipmentNeededDetailPanel: React.FC<EquipmentNeededDetailPanelProps> = ({ equipment = [] }) => {
  const displayItems = equipment.length > 0 ? equipment : ['bodyweight']

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Equipment Needed
      </h3>

      <div className="space-y-2 font-mono text-xs">
        {displayItems.map((item, idx) => {
          const formatted = item.replace(/_/g, ' ')
          const isBodyweight = formatted.toLowerCase() === 'bodyweight'
          const Icon = isBodyweight ? Box : Dumbbell

          return (
            <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="flex items-center gap-2">
                <Icon className="h-3.5 w-3.5 text-emerald-400" />
                <span className="font-semibold text-slate-200 capitalize">{formatted}</span>
              </div>
              <span className="text-slate-400 text-[11px] font-mono">
                {isBodyweight ? 'None' : 'Required'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

