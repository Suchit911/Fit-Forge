import React, { useState } from 'react'
import { Pause, Play, Maximize2 } from 'lucide-react'

export interface FormAnalysisViewportProps {
  image: string
}

export const FormAnalysisViewport: React.FC<FormAnalysisViewportProps> = ({ image }) => {
  const [isPlaying, setIsPlaying] = useState(true)
  const [speed, setSpeed] = useState('1.0x')

  return (
    <div className="relative aspect-[16/9] w-full rounded-3xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl group text-left">
      {/* Background Exercise Photo */}
      <img src={image} alt="Form Analysis Viewport" className="w-full h-full object-cover opacity-85" />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-slate-950/40" />

      {/* SVG Pose Skeleton & Landmark Overlay */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 1000 562">
        {/* Dashed Bar Path Trajectory Arc */}
        <path
          d="M 280 200 Q 500 150, 720 200"
          stroke="#10b981"
          strokeWidth="3"
          strokeDasharray="6,6"
          fill="none"
        />

        {/* Skeleton Lines */}
        {/* Shoulder to Elbow Left */}
        <line x1="380" y1="310" x2="280" y2="330" stroke="#10b981" strokeWidth="4" />
        {/* Elbow Left to Wrist Left */}
        <line x1="280" y1="330" x2="280" y2="200" stroke="#f97316" strokeWidth="4" />
        
        {/* Shoulder Right to Elbow Right */}
        <line x1="620" y1="310" x2="720" y2="330" stroke="#10b981" strokeWidth="4" />
        {/* Elbow Right to Wrist Right */}
        <line x1="720" y1="330" x2="720" y2="200" stroke="#10b981" strokeWidth="4" />

        {/* Torso Shoulder to Hips */}
        <line x1="380" y1="310" x2="620" y2="310" stroke="#10b981" strokeWidth="4" />
        <line x1="500" y1="310" x2="500" y2="450" stroke="#10b981" strokeWidth="4" />
        <line x1="450" y1="450" x2="550" y2="450" stroke="#10b981" strokeWidth="4" />

        {/* Landmark Joint Nodes */}
        <circle cx="380" cy="310" r="7" fill="#10b981" stroke="#0f172a" strokeWidth="2" />
        <circle cx="620" cy="310" r="7" fill="#10b981" stroke="#0f172a" strokeWidth="2" />

        <circle cx="280" cy="330" r="7" fill="#f97316" stroke="#0f172a" strokeWidth="2" />
        <circle cx="720" cy="330" r="7" fill="#10b981" stroke="#0f172a" strokeWidth="2" />

        <circle cx="280" cy="200" r="7" fill="#10b981" stroke="#0f172a" strokeWidth="2" />
        <circle cx="720" cy="200" r="7" fill="#10b981" stroke="#0f172a" strokeWidth="2" />

        <circle cx="450" cy="450" r="6" fill="#10b981" stroke="#0f172a" strokeWidth="2" />
        <circle cx="550" cy="450" r="6" fill="#10b981" stroke="#0f172a" strokeWidth="2" />
      </svg>

      {/* Floating Glassmorphism Cards on Body */}
      {/* Top Center: Bar Path */}
      <div className="absolute top-16 left-1/2 -translate-x-1/2 rounded-xl bg-slate-950/80 border border-emerald-500/40 px-3 py-1.5 backdrop-blur-md text-center shadow-lg">
        <span className="text-[9px] font-mono text-slate-400 uppercase block">Bar Path</span>
        <span className="text-xs font-extrabold text-emerald-400 font-mono">Good</span>
      </div>

      {/* Left: Elbow Angle */}
      <div className="absolute top-1/2 left-[18%] -translate-y-1/2 rounded-xl bg-slate-950/80 border border-emerald-500/40 px-3 py-1.5 backdrop-blur-md text-center shadow-lg">
        <span className="text-[9px] font-mono text-slate-400 uppercase block">Elbow Angle</span>
        <span className="text-sm font-extrabold text-emerald-400 font-mono">87°</span>
      </div>

      {/* Right: Wrist Angle */}
      <div className="absolute top-1/2 right-[18%] -translate-y-1/2 rounded-xl bg-slate-950/80 border border-emerald-500/40 px-3 py-1.5 backdrop-blur-md text-center shadow-lg">
        <span className="text-[9px] font-mono text-slate-400 uppercase block">Wrist Angle</span>
        <span className="text-sm font-extrabold text-emerald-400 font-mono">178°</span>
      </div>

      {/* Bottom Video Control Bar Overlay */}
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between gap-4 rounded-2xl bg-slate-950/80 border border-slate-800 p-3 backdrop-blur-md">
        
        {/* Play/Pause Button & Progress Timeline */}
        <div className="flex items-center gap-3 flex-1">
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer"
          >
            {isPlaying ? (
              <Pause className="h-4 w-4 fill-slate-950" />
            ) : (
              <Play className="h-4 w-4 fill-slate-950 ml-0.5" />
            )}
          </button>

          <div className="flex items-center gap-3 flex-1 font-mono text-xs text-slate-300">
            <span>00:16</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: '50%' }} />
            </div>
            <span>00:32</span>
          </div>
        </div>

        {/* Speed Selector & Fullscreen */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <select
            value={speed}
            onChange={(e) => setSpeed(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-slate-300 focus:outline-none cursor-pointer"
          >
            <option value="0.5x">0.5x</option>
            <option value="1.0x">1.0x</option>
            <option value="1.5x">1.5x</option>
          </select>

          <button
            type="button"
            aria-label="Fullscreen"
            className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>

      </div>
    </div>
  )
}
