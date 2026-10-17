import React, { useState } from 'react'
import { Modal } from '../ui'
import { Play, Pause, Maximize2 } from 'lucide-react'

export interface ExerciseVideoModalProps {
  isOpen: boolean
  onClose: () => void
  exerciseName: string
  image: string
}

export const ExerciseVideoModal: React.FC<ExerciseVideoModalProps> = ({
  isOpen,
  onClose,
  exerciseName,
  image,
}) => {
  const [isPlaying, setIsPlaying] = useState(true)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`${exerciseName} Demonstration`}>
      <div className="space-y-3 text-left pt-1">
        <div className="relative aspect-[16/9] w-full rounded-2xl overflow-hidden bg-slate-950 border border-slate-800">
          <img src={image} alt={exerciseName} className="w-full h-full object-cover opacity-85" />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent" />

          {/* Center Play/Pause Toggle */}
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex h-14 w-14 items-center justify-center rounded-full bg-slate-950/80 border border-slate-700 text-slate-100 shadow-2xl backdrop-blur-md hover:scale-110 transition-transform cursor-pointer"
          >
            {isPlaying ? (
              <Pause className="h-6 w-6 fill-slate-100" />
            ) : (
              <Play className="h-6 w-6 fill-slate-100 ml-0.5" />
            )}
          </button>

          {/* Timeline Bar */}
          <div className="absolute bottom-3 left-3 right-3 flex items-center gap-3 text-[11px] font-mono text-slate-300">
            <span>00:12</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: '40%' }} />
            </div>
            <span>00:30</span>
            <Maximize2 className="h-4 w-4 text-slate-400" />
          </div>
        </div>

        <p className="text-xs text-slate-400">
          HD technique video demonstration showing optimal path and lockouts.
        </p>
      </div>
    </Modal>
  )
}
