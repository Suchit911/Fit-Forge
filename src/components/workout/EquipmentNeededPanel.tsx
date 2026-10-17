import React from 'react'
import { Dumbbell, Layers, Wrench, Box } from 'lucide-react'

export const EquipmentNeededPanel: React.FC = () => {
  const equipmentList = [
    { name: 'Barbell', qty: '1', icon: Dumbbell },
    { name: 'Dumbbells', qty: 'Pair', icon: Dumbbell },
    { name: 'Cable Machine', qty: '1', icon: Wrench },
    { name: 'Bench', qty: '1', icon: Box },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80">
        <Layers className="h-4 w-4 text-emerald-400" />
        <h3 className="text-sm font-extrabold text-slate-100">Equipment Needed</h3>
      </div>

      <div className="space-y-2">
        {equipmentList.map((item, idx) => {
          const Icon = item.icon
          return (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs"
            >
              <div className="flex items-center gap-2.5">
                <Icon className="h-3.5 w-3.5 text-slate-400" />
                <span className="font-semibold text-slate-200">{item.name}</span>
              </div>
              <span className="font-mono text-slate-400 text-[11px]">{item.qty}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
