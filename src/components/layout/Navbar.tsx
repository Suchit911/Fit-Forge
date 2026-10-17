import React from 'react'
import { Menu, Flame, Bell, User as UserIcon, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useUser, useNotifications } from '../../hooks'

export interface NavbarProps {
  onOpenMobileDrawer: () => void
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenMobileDrawer }) => {
  const { user, authUser, isAuthenticated, logout } = useUser()
  const navigate = useNavigate()
  const { unreadCount = 0 } = useNotifications()

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-800/80 bg-slate-950/90 px-4 md:px-6 backdrop-blur-md">
      {/* Mobile Drawer Trigger & Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileDrawer}
          className="lg:hidden rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-200 transition-colors cursor-pointer"
          aria-label="Open mobile menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div
          onClick={() => navigate('/dashboard')}
          className="flex lg:hidden items-center gap-2 cursor-pointer"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 text-slate-950 font-bold shadow-md shadow-emerald-500/20">
            <Flame className="h-5 w-5" />
          </div>
          <span className="text-sm font-extrabold text-slate-100 tracking-tight">AI FITNESS</span>
        </div>
      </div>

      {/* Top Header Actions */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/notifications')}
          aria-label={`Notifications (${unreadCount} unread)`}
          className="relative rounded-xl border border-slate-800 bg-slate-900/90 p-2 text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-colors cursor-pointer"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-slate-950">
              {unreadCount}
            </span>
          )}
        </button>

        <div
          onClick={() => navigate('/profile')}
          className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-1.5 text-left cursor-pointer hover:border-slate-700 transition-colors"
          role="button"
          tabIndex={0}
          aria-label="View Profile"
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
          <div className="hidden sm:block text-left">
            <p className="text-xs font-bold text-slate-100">{user?.name || authUser?.displayName || authUser?.email?.split('@')[0] || 'Athlete'}</p>
            <p className="text-[10px] text-emerald-400 font-mono">Member</p>
          </div>
        </div>

        {isAuthenticated && (
          <button
            type="button"
            onClick={async () => {
              await logout()
              navigate('/login')
            }}
            title="Log Out"
            aria-label="Log Out"
            className="rounded-xl border border-slate-800 bg-slate-900/90 p-2 text-slate-400 hover:text-rose-400 hover:border-rose-900/50 focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition-colors cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </div>
    </header>
  )
}
