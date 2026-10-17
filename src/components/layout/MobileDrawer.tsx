import React, { useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { X, Flame } from 'lucide-react'
import { navItemsMain, navItemsSecondary } from './Sidebar'
import { cn } from '../../lib/utils'

export interface MobileDrawerProps {
  isOpen: boolean
  onClose: () => void
}

export const MobileDrawer: React.FC<MobileDrawerProps> = ({ isOpen, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', handleKeyDown)
    } else {
      document.body.style.overflow = 'auto'
    }
    return () => {
      document.body.style.overflow = 'auto'
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer Panel */}
      <aside className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-slate-950 p-6 text-slate-300 shadow-2xl border-r border-slate-800">
        <div className="flex items-center justify-between pb-6 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-slate-950 font-bold shadow-md shadow-emerald-500/20">
              <Flame className="h-5 w-5" />
            </div>
            <span className="text-base font-extrabold text-slate-100 tracking-tight">AI FITNESS</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close navigation drawer"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-200 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-6 flex-1 space-y-1.5 overflow-y-auto pr-1">
          {navItemsMain.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3.5 py-3 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-slate-900 text-emerald-400 font-semibold border-l-2 border-emerald-500 shadow-sm shadow-emerald-950/50'
                      : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-200'
                  )
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}

          <div className="my-3 border-t border-slate-800/80" />

          {navItemsSecondary.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3.5 py-3 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-slate-900 text-emerald-400 font-semibold border-l-2 border-emerald-500 shadow-sm shadow-emerald-950/50'
                      : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-200'
                  )
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </aside>
    </div>
  )
}
