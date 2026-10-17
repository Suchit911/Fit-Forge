import React from 'react'
import { AudioPlaylistControl } from '../layout/HeaderControls'

export interface FormAnalysisHeaderProps {
  exerciseTitle: string
}

export const FormAnalysisHeader: React.FC<FormAnalysisHeaderProps> = ({ exerciseTitle }) => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Title */}
      <div className="text-left flex items-center gap-3">
        <h1 className="text-xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
          Form Analysis
        </h1>
        <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-0.5 text-xs font-mono font-bold">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
          {exerciseTitle} Analysis
        </span>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Audio / Playlist Controls */}
        <AudioPlaylistControl />
      </div>
    </header>
  )
}
