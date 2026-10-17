import React from 'react'
import type { NotificationItemData } from '../../types'
import { NotificationItem } from './NotificationItem'
import { NotificationEmptyState } from './NotificationEmptyState'

export interface NotificationFeedProps {
  notifications: NotificationItemData[]
  onMarkAsRead: (id: string) => void
}

export const NotificationFeed: React.FC<NotificationFeedProps> = ({ notifications, onMarkAsRead }) => {
  if (notifications.length === 0) {
    return <NotificationEmptyState />
  }

  const today = notifications.filter((n) => n.dateGroup === 'Today')
  const yesterday = notifications.filter((n) => n.dateGroup === 'Yesterday')
  const earlier = notifications.filter((n) => n.dateGroup === 'Earlier')

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-6 text-left shadow-2xl">
      {/* Today Section */}
      {today.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-extrabold text-slate-300 uppercase tracking-wider pb-1 border-b border-slate-800/80">
            Today
          </h3>
          <div className="space-y-2.5">
            {today.map((n) => (
              <NotificationItem key={n.id} notification={n} onMarkAsRead={onMarkAsRead} />
            ))}
          </div>
        </div>
      )}

      {/* Yesterday Section */}
      {yesterday.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-extrabold text-slate-400 uppercase tracking-wider pb-1 border-b border-slate-800/80">
            Yesterday
          </h3>
          <div className="space-y-2.5">
            {yesterday.map((n) => (
              <NotificationItem key={n.id} notification={n} onMarkAsRead={onMarkAsRead} />
            ))}
          </div>
        </div>
      )}

      {/* Earlier Section */}
      {earlier.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-extrabold text-slate-500 uppercase tracking-wider pb-1 border-b border-slate-800/80">
            Earlier
          </h3>
          <div className="space-y-2.5 opacity-85">
            {earlier.map((n) => (
              <NotificationItem key={n.id} notification={n} onMarkAsRead={onMarkAsRead} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
