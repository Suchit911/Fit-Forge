import React from 'react'

export interface BrowseMuscleGroupSectionProps {
  onSelectMuscle: (muscle: string) => void
}

export const BrowseMuscleGroupSection: React.FC<BrowseMuscleGroupSectionProps> = ({ onSelectMuscle }) => {
  const groups = [
    { name: 'Chest', count: '42 exercises', key: 'chest' },
    { name: 'Back', count: '56 exercises', key: 'back' },
    { name: 'Shoulders', count: '32 exercises', key: 'shoulders' },
    { name: 'Arms', count: '28 exercises', key: 'arms' },
    { name: 'Legs', count: '48 exercises', key: 'legs' },
    { name: 'Core', count: '24 exercises', key: 'core' },
  ]

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-extrabold text-slate-100">Browse by Muscle Group</h2>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {groups.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => onSelectMuscle(item.key)}
            className="group rounded-2xl border border-slate-800 bg-slate-900/90 p-4 text-center space-y-3 transition-all hover:border-emerald-500/50 hover:bg-slate-900 cursor-pointer"
          >
            {/* Anatomical Silhouette Graphic */}
            <div className="flex justify-center h-20 items-center">
              <svg className="h-16 w-14 text-slate-700" viewBox="0 0 100 150" fill="none">
                <circle cx="50" cy="18" r="10" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
                <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="currentColor" strokeWidth="2" fill="#0f172a" />
                <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="currentColor" strokeWidth="3" />
                <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="currentColor" strokeWidth="4" />
                
                {/* Specific Highlighted Muscle Overlay */}
                {item.key === 'chest' && (
                  <path d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z" fill="#ef4444" stroke="#f97316" strokeWidth="1.5" />
                )}
                {item.key === 'back' && (
                  <path d="M35 42 L 65 42 L 60 80 L 40 80 Z" fill="#ef4444" stroke="#f97316" strokeWidth="1.5" />
                )}
                {item.key === 'shoulders' && (
                  <circle cx="32" cy="38" r="6" fill="#ef4444" />
                )}
                {item.key === 'shoulders' && (
                  <circle cx="68" cy="38" r="6" fill="#ef4444" />
                )}
                {item.key === 'arms' && (
                  <path d="M26 45 L 20 75 M 74 45 L 80 75" stroke="#ef4444" strokeWidth="4" />
                )}
                {item.key === 'legs' && (
                  <path d="M42 88 L 39 135 M 58 88 L 61 135" stroke="#ef4444" strokeWidth="5" />
                )}
                {item.key === 'core' && (
                  <rect x="42" y="60" width="16" height="22" rx="3" fill="#ef4444" />
                )}
              </svg>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                {item.name}
              </h4>
              <span className="text-[10px] text-slate-400 font-mono block mt-0.5">{item.count}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
