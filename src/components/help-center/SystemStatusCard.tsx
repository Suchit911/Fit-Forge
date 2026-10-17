import React from 'react'
import type { SystemStatusRow } from '../../types'
import { Bot, Dumbbell, Utensils, Video, Watch, ChevronRight } from 'lucide-react'

export interface SystemStatusCardProps {
  statusRows: SystemStatusRow[]
  onViewDetailedStatusClick: () => void
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  statusRows,
  onViewDetailedStatusClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'bot':
        return <Bot className="h-4 w-4 text-purple-400" />
      case 'dumbbell':
        return <Dumbbell className="h-4 w-4 text-blue-400" />
      case 'utensils':
        return <Utensils className="h-4 w-4 text-orange-400" />
      case 'video':
        return <Video className="h-4 w-4 text-emerald-400" />
      default:
        return <Watch className="h-4 w-4 text-cyan-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">System Status</h3>
        <span className="text-[10px] font-mono font-extrabold text-emerald-400">
          All Systems Operational
        </span>
      </div>

      <div className="space-y-2 font-mono text-xs">
        {statusRows.map((row) => (
          <div
            key={row.id}
            className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/80"
          >
            <div className="flex items-center gap-2">
              {getIcon(row.iconName)}
              <span className="font-bold text-slate-300">{row.serviceName}</span>
            </div>
            <span className="text-[10px] font-extrabold text-emerald-400 flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-400" /> Operational
            </span>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onViewDetailedStatusClick}
          className="flex items-center justify-between w-full text-xs font-mono text-blue-400 hover:text-blue-300 font-bold transition-colors cursor-pointer"
        >
          <span>View detailed status page</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
