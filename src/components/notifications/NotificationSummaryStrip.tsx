import React from 'react'
import { Bell, Calendar, Clock, AlertTriangle } from 'lucide-react'

export interface NotificationSummaryStripProps {
  unreadCount?: number
  todayCount?: number
  weekCount?: number
  importantCount?: number
}

export const NotificationSummaryStrip: React.FC<NotificationSummaryStripProps> = ({
  unreadCount = 3,
  todayCount = 5,
  weekCount = 18,
  importantCount = 2,
}) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-left font-mono">
      {/* Unread */}
      <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/90 p-4 space-y-1 shadow-lg shadow-emerald-950/20">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-bold uppercase">Unread</span>
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Bell className="h-4 w-4" />
          </div>
        </div>
        <span className="text-2xl font-extrabold text-emerald-400 block">{unreadCount}</span>
      </div>

      {/* Today */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-1 shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-bold uppercase">Today</span>
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="h-4 w-4" />
          </div>
        </div>
        <span className="text-2xl font-extrabold text-slate-100 block">{todayCount}</span>
      </div>

      {/* This Week */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-1 shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-bold uppercase">This Week</span>
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Calendar className="h-4 w-4" />
          </div>
        </div>
        <span className="text-2xl font-extrabold text-slate-100 block">{weekCount}</span>
      </div>

      {/* Important */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-1 shadow-lg">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-bold uppercase">Important</span>
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-4 w-4" />
          </div>
        </div>
        <span className="text-2xl font-extrabold text-amber-400 block">{importantCount}</span>
      </div>
    </div>
  )
}
