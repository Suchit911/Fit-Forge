import React from 'react'
import { Plus } from 'lucide-react'
import { AudioPlaylistControl } from '../layout/HeaderControls'

export interface AchievementsHeaderProps {
  onAddAchievementClick: () => void
}

export const AchievementsHeader: React.FC<AchievementsHeaderProps> = ({ onAddAchievementClick }) => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Title */}
      <div className="text-left">
        <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">Achievements</h1>
        <p className="text-xs text-slate-400 mt-1 font-medium">
          Celebrate your milestones and unlock new rewards
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* + Add Achievement Button */}
        <button
          type="button"
          onClick={onAddAchievementClick}
          className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500 hover:text-slate-950 px-3.5 py-2 text-xs font-extrabold text-emerald-400 transition-all cursor-pointer shadow-md shadow-emerald-950/40"
        >
          <Plus className="h-4 w-4" /> Add Achievement
        </button>

        {/* Audio / Playlist Controls */}
        <AudioPlaylistControl />
      </div>
    </header>
  )
}
