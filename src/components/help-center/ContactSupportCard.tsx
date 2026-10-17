import React from 'react'
import type { ContactOptionRow } from '../../types'
import { MessageSquare, Mail, AlertTriangle, ChevronRight } from 'lucide-react'

export interface ContactSupportCardProps {
  options: ContactOptionRow[]
  onOptionClick: (opt: ContactOptionRow) => void
  onViewAllClick: () => void
}

export const ContactSupportCard: React.FC<ContactSupportCardProps> = ({
  options,
  onOptionClick,
  onViewAllClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'message-square':
        return <MessageSquare className="h-4 w-4 text-emerald-400" />
      case 'mail':
        return <Mail className="h-4 w-4 text-blue-400" />
      default:
        return <AlertTriangle className="h-4 w-4 text-amber-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="space-y-0.5 pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Contact Support</h3>
        <p className="text-[10px] text-slate-400 font-sans">We're here to help!</p>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {options.map((opt) => (
          <div
            key={opt.id}
            onClick={() => onOptionClick(opt)}
            className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 shrink-0">
                {getIcon(opt.iconName)}
              </div>
              <div className="space-y-0.5 font-sans">
                <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                  {opt.title}
                </h4>
                <p className="text-[10px] text-slate-400">{opt.description}</p>
              </div>
            </div>

            <span className="text-[10px] font-mono font-bold text-emerald-400 flex items-center gap-1 shrink-0">
              {opt.statusAction}
            </span>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onViewAllClick}
          className="flex items-center justify-between w-full text-xs font-mono text-emerald-400 hover:text-emerald-300 font-bold transition-colors cursor-pointer"
        >
          <span>View all support options</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
