import React from 'react'
import { Dumbbell, Wrench, Activity, Anchor } from 'lucide-react'

export interface EquipmentTypesSidebarCardProps {
  onSelectEquipment: (eq: string) => void
}

export const EquipmentTypesSidebarCard: React.FC<EquipmentTypesSidebarCardProps> = ({ onSelectEquipment }) => {
  const items = [
    { name: 'Barbell', count: '156 exercises', icon: Dumbbell, key: 'barbell' },
    { name: 'Dumbbells', count: '142 exercises', icon: Dumbbell, key: 'dumbbells' },
    { name: 'Cable Machine', count: '98 exercises', icon: Wrench, key: 'cable_machine' },
    { name: 'Bodyweight', count: '76 exercises', icon: Activity, key: 'bodyweight' },
    { name: 'Kettlebells', count: '40 exercises', icon: Anchor, key: 'kettlebells' },
    { name: 'Resistance Bands', count: '32 exercises', icon: Activity, key: 'resistance_bands' },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Equipment Types</h3>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      <div className="space-y-2">
        {items.map((eq) => {
          const Icon = eq.icon
          return (
            <button
              key={eq.key}
              type="button"
              onClick={() => onSelectEquipment(eq.key)}
              className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors text-left cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 text-emerald-400 shrink-0" />
                <span className="text-xs font-bold text-slate-200">{eq.name}</span>
              </div>
              <span className="text-[10px] font-mono text-slate-400">{eq.count}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
