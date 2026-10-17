import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Dumbbell,
  BookOpen,
  Utensils,
  TrendingUp,
  Bot,
  Camera,
  Trophy,
  User,
  Settings,
  HelpCircle,
  Flame,
  Crown,
  Check,
} from 'lucide-react'
import { cn } from '../../lib/utils'

export const navItemsMain = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Workouts', path: '/workouts', icon: Dumbbell },
  { label: 'Exercises', path: '/exercises', icon: BookOpen },
  { label: 'Nutrition', path: '/nutrition', icon: Utensils },
  { label: 'Progress', path: '/progress', icon: TrendingUp },
  { label: 'AI Coach', path: '/coach', icon: Bot },
  { label: 'Form Analysis', path: '/form-analysis', icon: Camera },
  { label: 'Achievements', path: '/achievements', icon: Trophy },
]

export const navItemsSecondary = [
  { label: 'Profile', path: '/profile', icon: User },
  { label: 'Settings', path: '/settings', icon: Settings },
  { label: 'Help Center', path: '/help-center', icon: HelpCircle },
]

import { useToast } from '../ui/Toast'
import { useUser } from '../../hooks/useUser'

export const Sidebar: React.FC = () => {
  const { showToast } = useToast()
  const { user } = useUser()
  const streak = user?.streakDays ?? 0
  const days = [
    { label: 'S', checked: streak >= 7 },
    { label: 'M', checked: streak >= 1 },
    { label: 'T', checked: streak >= 2 },
    { label: 'W', checked: streak >= 3 },
    { label: 'T', checked: streak >= 4 },
    { label: 'F', checked: streak >= 5 },
    { label: 'S', checked: streak >= 6 },
  ]

  return (
    <aside className="hidden lg:flex flex-col w-64 border-r border-slate-800/80 bg-slate-950 px-4 py-6 text-slate-300 min-h-screen shrink-0 text-left justify-between">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2 pb-6 border-b border-slate-800/80">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-slate-950 font-bold shadow-lg shadow-emerald-500/20">
            <Flame className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-extrabold text-slate-100 tracking-tight">AI FITNESS</h1>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Your AI Fitness Coach</p>
          </div>
        </div>

        {/* Main Navigation List */}
        <nav className="mt-5 space-y-1">
          {navItemsMain.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all',
                    isActive
                      ? 'bg-gradient-to-r from-emerald-950 to-slate-900 text-emerald-400 border border-emerald-500/30 shadow-md shadow-emerald-950/40'
                      : 'text-slate-400 hover:bg-slate-900/80 hover:text-slate-200'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Divider */}
        <div className="my-4 border-t border-slate-900" />

        {/* Secondary Navigation */}
        <nav className="space-y-1">
          {navItemsSecondary.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-xl px-3.5 py-2 text-xs font-medium transition-colors',
                    isActive
                      ? 'bg-slate-900 text-emerald-400'
                      : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-200'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* Lower Cards Container */}
      <div className="space-y-4 pt-4 border-t border-slate-900">
        
        {/* Current Streak Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-amber-400" />
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-mono block">Current Streak</span>
              <h4 className="text-sm font-extrabold text-slate-100">{streak} {streak === 1 ? 'Day' : 'Days'}</h4>
            </div>
          </div>
          <p className="text-[11px] text-slate-400">
            {streak > 0 ? "Keep it up! You're on fire!" : 'Log your workouts to build your streak!'}
          </p>
          
          {/* Day Checks */}
          <div className="flex justify-between items-center pt-1 text-[10px]">
            {days.map((d, idx) => (
              <div key={idx} className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    'h-4 w-4 rounded-full flex items-center justify-center border text-[8px]',
                    d.checked
                      ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400 font-bold'
                      : 'border-slate-800 text-slate-600'
                  )}
                >
                  {d.checked ? <Check className="h-2.5 w-2.5" /> : null}
                </div>
                <span className="text-slate-500 font-mono">{d.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Upgrade to Pro Promotional Card */}
        <div className="relative rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 p-4 text-center space-y-2 overflow-hidden">
          <div className="mx-auto flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Crown className="h-5 w-5" />
          </div>
          <h4 className="text-xs font-extrabold text-slate-100">Upgrade to Pro</h4>
          <p className="text-[10px] text-slate-400 leading-tight">
            Unlock advanced AI insights, custom plans & more.
          </p>
          <button
            type="button"
            onClick={() => showToast('AI FITNESS Pro tier requested! Upgrading subscription...', 'info')}
            className="w-full rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 py-2 text-xs font-bold shadow-md shadow-emerald-500/20 transition-all cursor-pointer"
          >
            Upgrade Now
          </button>
        </div>

      </div>
    </aside>
  )
}
