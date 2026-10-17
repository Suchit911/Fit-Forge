import React from 'react'
import type { NotificationItemData } from '../../types'
import { Dumbbell, Bot, Utensils, Trophy, TrendingUp, Moon, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export interface NotificationItemProps {
  notification: NotificationItemData
  onMarkAsRead: (id: string) => void
}

export const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onMarkAsRead }) => {
  const navigate = useNavigate()

  const getIcon = (category: string) => {
    switch (category) {
      case 'Workout':
        return <Dumbbell className="h-4 w-4 text-emerald-400" />
      case 'AI Coach':
        return <Bot className="h-4 w-4 text-purple-400" />
      case 'Nutrition':
        return <Utensils className="h-4 w-4 text-cyan-400" />
      case 'Achievement':
        return <Trophy className="h-4 w-4 text-amber-400" />
      case 'Progress':
        return <TrendingUp className="h-4 w-4 text-blue-400" />
      case 'Recovery':
        return <Moon className="h-4 w-4 text-indigo-400" />
      default:
        return <Shield className="h-4 w-4 text-slate-400" />
    }
  }

  const handleActionClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onMarkAsRead(notification.id)
    if (notification.actionRoute) {
      navigate(notification.actionRoute)
    }
  }

  return (
    <div
      onClick={() => onMarkAsRead(notification.id)}
      className={`group flex items-start justify-between gap-4 p-4 rounded-2xl border transition-all cursor-pointer ${
        !notification.read
          ? 'border-emerald-500/30 bg-slate-950/80 shadow-md shadow-emerald-950/20'
          : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-700 opacity-90'
      }`}
    >
      <div className="flex items-start gap-3 text-left">
        {/* Category Icon */}
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 border border-slate-800 shrink-0 mt-0.5">
          {getIcon(notification.category)}
        </div>

        {/* Text Content */}
        <div className="space-y-1 font-sans">
          <div className="flex items-center gap-2">
            <h4 className={`text-xs font-bold ${!notification.read ? 'text-slate-100' : 'text-slate-300'}`}>
              {notification.title}
            </h4>

            {/* Unread indicator dot */}
            {!notification.read && (
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500/50 shrink-0" />
            )}
          </div>

          <p className="text-xs text-slate-400 leading-relaxed max-w-xl">{notification.message}</p>

          <div className="flex items-center gap-3 pt-1 font-mono text-[10px]">
            <span className="text-slate-500 font-medium">{notification.timestamp}</span>
            <span className="px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-slate-400 font-bold">
              {notification.category}
            </span>
          </div>
        </div>
      </div>

      {/* Right Action Link Button */}
      {notification.actionLabel && (
        <button
          type="button"
          onClick={handleActionClick}
          className="shrink-0 flex items-center gap-1 text-xs font-mono font-bold text-emerald-400 hover:text-emerald-300 transition-colors pt-1 cursor-pointer"
        >
          <span>{notification.actionLabel}</span>
        </button>
      )}
    </div>
  )
}
