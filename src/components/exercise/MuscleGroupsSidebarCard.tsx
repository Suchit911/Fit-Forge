import React from 'react'

export interface MuscleGroupsSidebarCardProps {
  onSelectMuscle: (muscle: string) => void
}

export const MuscleGroupsSidebarCard: React.FC<MuscleGroupsSidebarCardProps> = ({ onSelectMuscle }) => {
  const groups = [
    { name: 'Chest', count: 42, pct: '75%', key: 'chest' },
    { name: 'Back', count: 56, pct: '100%', key: 'back' },
    { name: 'Shoulders', count: 32, pct: '57%', key: 'shoulders' },
    { name: 'Arms', count: 28, pct: '50%', key: 'arms' },
    { name: 'Legs', count: 48, pct: '85%', key: 'legs' },
    { name: 'Core', count: 24, pct: '42%', key: 'core' },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Muscle Groups</h3>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      <div className="space-y-3">
        {groups.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => onSelectMuscle(m.key)}
            className="w-full space-y-1 group text-left cursor-pointer"
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-200 group-hover:text-emerald-400 transition-colors">
                {m.name}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">{m.count} exercises</span>
            </div>
            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: m.pct }} />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
