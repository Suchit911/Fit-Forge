import React from 'react'
import type { ImportantUpdateItem } from '../../types'
import { AlertCircle, Bot, Shield, Trophy } from 'lucide-react'

export interface ImportantUpdatesCardProps {
  updates: ImportantUpdateItem[]
}

export const ImportantUpdatesCard: React.FC<ImportantUpdatesCardProps> = ({ updates }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'bot':
        return <Bot className="h-4 w-4 text-purple-400" />
      case 'shield':
        return <Shield className="h-4 w-4 text-emerald-400" />
      default:
        return <Trophy className="h-4 w-4 text-amber-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
          <AlertCircle className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Important Updates</h3>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {updates.map((item) => (
          <div
            key={item.id}
            className="flex items-start justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800"
          >
            <div className="flex items-start gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 shrink-0 mt-0.5">
                {getIcon(item.iconName)}
              </div>
              <div className="space-y-0.5 font-sans">
                <h4 className="text-xs font-bold text-slate-100">{item.title}</h4>
                <p className="text-[10px] text-slate-400 leading-tight">{item.description}</p>
              </div>
            </div>
            <span className="text-[9px] font-mono text-slate-500 shrink-0 ml-2 pt-0.5">{item.timeAgo}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
