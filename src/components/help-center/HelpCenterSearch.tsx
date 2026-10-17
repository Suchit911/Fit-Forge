import React, { useEffect, useRef } from 'react'
import { Search } from 'lucide-react'

export interface HelpCenterSearchProps {
  value: string
  onChange: (val: string) => void
}

export const HelpCenterSearch: React.FC<HelpCenterSearchProps> = ({ value, onChange }) => {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="relative w-full">
      <div className="relative flex items-center">
        <Search className="absolute left-4 h-5 w-5 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search for articles, workouts, nutrition, or anything else..."
          className="w-full h-12 rounded-2xl border border-emerald-500/30 bg-slate-900/90 pl-12 pr-16 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 shadow-lg transition-all"
        />
        <div className="absolute right-4 flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-400">
          <span>⌘</span>
          <span>K</span>
        </div>
      </div>
    </div>
  )
}
