import React, { useEffect, useState } from 'react'
import { Bell, ChevronDown, User as UserIcon, Music, Volume2, VolumeX } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useUser, useNotifications } from '../../hooks'
import { useToast } from '../ui/Toast'

export const NotificationBell: React.FC = () => {
  const navigate = useNavigate()
  const { unreadCount = 0 } = useNotifications()

  return (
    <button
      type="button"
      onClick={() => navigate('/notifications')}
      aria-label={`Notifications (${unreadCount} unread)`}
      className="relative rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-colors cursor-pointer"
    >
      <Bell className="h-4 w-4" />
      {unreadCount > 0 && (
        <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-slate-950">
          {unreadCount}
        </span>
      )}
    </button>
  )
}

export const UserProfilePill: React.FC = () => {
  const navigate = useNavigate()
  const { user, authUser } = useUser()

  return (
    <div
      onClick={() => navigate('/profile')}
      className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-left cursor-pointer hover:border-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-colors"
      role="button"
      tabIndex={0}
      aria-label="View user profile"
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate('/profile')
        }
      }}
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-emerald-500 to-cyan-500 text-slate-950 font-bold">
        <UserIcon className="h-4 w-4" />
      </div>
      <div className="hidden sm:block">
        <h4 className="text-xs font-bold text-slate-100">{user?.name || authUser?.displayName || authUser?.email?.split('@')[0] || 'Athlete'}</h4>
        <span className="text-[10px] text-emerald-400 font-mono">Member</span>
      </div>
      <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
    </div>
  )
}

export const AudioPlaylistControl: React.FC = () => {
  const { showToast } = useToast()
  const [muted, setMuted] = useState(false)
  const [playlist, setPlaylist] = useState('Gym Playlist')

  const toggleMute = () => {
    setMuted(!muted)
    showToast(muted ? 'Audio unmuted' : 'Audio muted', 'info')
  }

  const cyclePlaylist = () => {
    const playlists = ['Gym Playlist', 'Beats & Cardio', 'Heavy Metal Lifts', 'Lo-Fi Chill Rest']
    const nextIdx = (playlists.indexOf(playlist) + 1) % playlists.length
    const nextName = playlists[nextIdx]
    setPlaylist(nextName)
    showToast(`Switched playlist to: ${nextName}`, 'info')
  }

  return (
    <div className="flex items-center gap-2">
      {/* Music Playlist Selector */}
      <button
        type="button"
        onClick={cyclePlaylist}
        aria-label="Select audio playlist"
        className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-1.5 text-xs font-mono text-slate-300 hover:border-slate-700 transition-colors cursor-pointer"
      >
        <Music className="h-3.5 w-3.5 text-emerald-400" />
        <span className="truncate max-w-[100px] sm:max-w-none">{playlist}</span>
        <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
      </button>

      {/* Volume Button */}
      <button
        type="button"
        onClick={toggleMute}
        aria-label={muted ? 'Unmute audio' : 'Mute audio'}
        className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-colors cursor-pointer"
      >
        {muted ? <VolumeX className="h-4 w-4 text-red-400" /> : <Volume2 className="h-4 w-4 text-slate-400" />}
      </button>
    </div>
  )
}

export function useSearchShortcut(inputRef: React.RefObject<HTMLInputElement | null>) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      } else if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        inputRef.current?.blur()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [inputRef])
}
