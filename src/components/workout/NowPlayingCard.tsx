import React, { useState } from 'react'
import { Play, Pause, SkipBack, SkipForward, Music } from 'lucide-react'

export const NowPlayingCard: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState(true)

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-4 flex items-center justify-between gap-3 text-left">
      {/* Cover & Song info */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="h-12 w-12 rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
          <img src="/assets/album_art_stronger.jpg" alt="Stronger Album Cover" className="w-full h-full object-cover" />
        </div>
        <div className="space-y-0.5 truncate">
          <span className="text-[10px] text-slate-500 font-mono uppercase font-bold flex items-center gap-1">
            <Music className="h-3 w-3 text-emerald-400" /> Now Playing
          </span>
          <h4 className="text-xs font-extrabold text-slate-100 truncate">Stronger</h4>
          <p className="text-[10px] text-slate-400 font-medium truncate">Kanye West</p>
        </div>
      </div>

      {/* Audio Controls */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          type="button"
          aria-label="Previous track"
          className="p-1.5 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <SkipBack className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20 transition-all cursor-pointer"
        >
          {isPlaying ? (
            <Pause className="h-4 w-4 fill-slate-950" />
          ) : (
            <Play className="h-4 w-4 fill-slate-950 ml-0.5" />
          )}
        </button>

        <button
          type="button"
          aria-label="Next track"
          className="p-1.5 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <SkipForward className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
