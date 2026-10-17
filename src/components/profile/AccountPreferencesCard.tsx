import React from 'react'
import type { AccountPreferenceRow } from '../../types'
import { Bell, Lock, Smartphone, ChevronRight } from 'lucide-react'

export interface AccountPreferencesCardProps {
  rows: AccountPreferenceRow[]
  onManageClick: () => void
  onRowClick: (id: string) => void
}

export const AccountPreferencesCard: React.FC<AccountPreferencesCardProps> = ({
  rows,
  onManageClick,
  onRowClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'bell':
        return <Bell className="h-4 w-4 text-purple-400" />
      case 'lock':
        return <Lock className="h-4 w-4 text-emerald-400" />
      default:
        return <Smartphone className="h-4 w-4 text-cyan-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Account & Preferences</h3>
        <button
          type="button"
          onClick={onManageClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          Manage
        </button>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {rows.map((r) => (
          <div
            key={r.id}
            onClick={() => onRowClick(r.id)}
            className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 shrink-0">
                {getIcon(r.iconName)}
              </div>
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                  {r.title}
                </h4>
                <p className="text-[10px] text-slate-400 font-sans">{r.description}</p>
              </div>
            </div>

            <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-slate-200 transition-colors shrink-0" />
          </div>
        ))}
      </div>
    </div>
  )
}
