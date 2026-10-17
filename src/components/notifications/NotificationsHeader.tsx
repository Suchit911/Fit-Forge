import React from 'react'
import { AudioPlaylistControl } from '../layout/HeaderControls'

export interface NotificationsHeaderProps {
  unreadCount?: number
}

export const NotificationsHeader: React.FC<NotificationsHeaderProps> = () => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      {/* Left Title */}
      <div className="text-left">
        <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight">Notifications</h1>
        <p className="text-xs text-slate-400 mt-1 font-medium">
          Stay updated on your fitness journey
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Audio / Playlist Controls */}
        <AudioPlaylistControl />
      </div>
    </header>
  )
}
