import React from 'react'

export interface UpNextExerciseItem {
  num: number
  index: number
  name: string
  setsReps: string
  rest: string
  image: string
  slotRole?: string
  exerciseId?: string
}

export interface UpNextSectionProps {
  upcomingExercises?: UpNextExerciseItem[]
  onSelectExercise?: (index: number) => void
}

export const UpNextSection: React.FC<UpNextSectionProps> = ({
  upcomingExercises = [],
  onSelectExercise,
}) => {
  const items = upcomingExercises

  if (items.length === 0) {
    return (
      <div className="p-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 text-center">
        <p className="text-xs font-mono text-emerald-400 font-bold">
          Final Exercise — Complete remaining sets to finish workout!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3 text-left">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-extrabold text-slate-100">Up Next</h3>
        <span className="text-xs font-mono text-slate-500">
          {items.length} {items.length === 1 ? 'Exercise' : 'Exercises'} Remaining
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((item) => (
          <div
            key={`${item.num}_${item.name}`}
            onClick={() => onSelectExercise && onSelectExercise(item.index)}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && onSelectExercise) {
                e.preventDefault()
                onSelectExercise(item.index)
              }
            }}
            tabIndex={onSelectExercise ? 0 : undefined}
            role={onSelectExercise ? 'button' : undefined}
            aria-label={`Jump to exercise ${item.num}: ${item.name}`}
            className={`flex items-center gap-3 p-3 rounded-2xl border border-slate-800 bg-slate-900/90 transition-all ${
              onSelectExercise
                ? 'cursor-pointer hover:border-slate-700 hover:bg-slate-850 focus:outline-none focus:ring-2 focus:ring-emerald-500'
                : ''
            }`}
          >
            <div className="relative h-12 w-16 rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
              <img src={item.image} alt={item.name} className="w-full h-full object-cover opacity-80" />
              <span className="absolute top-1 left-1 flex h-4 w-4 items-center justify-center rounded-full bg-slate-950/80 border border-slate-700 text-[9px] font-mono font-bold text-slate-200">
                {item.num}
              </span>
            </div>

            <div className="space-y-0.5 min-w-0">
              <h4 className="text-xs font-bold text-slate-100 truncate">{item.name}</h4>
              {item.slotRole && (
                <p className="text-[9px] font-mono text-emerald-400 capitalize truncate">
                  {item.slotRole.replace(/_/g, ' ')}
                </p>
              )}
              <p className="text-[10px] font-mono text-slate-400">{item.setsReps}</p>
              <p className="text-[9px] font-mono text-slate-500">{item.rest}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

