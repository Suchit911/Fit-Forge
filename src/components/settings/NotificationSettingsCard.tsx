import React from 'react'
import type { NotificationSettingsData } from '../../types'
import { Bell, Dumbbell, Timer, Trophy, Apple, Bot, BarChart2, ChevronRight } from 'lucide-react'

export interface NotificationSettingsCardProps {
  notifications: NotificationSettingsData
  onToggle: (key: keyof NotificationSettingsData) => void
  onManageClick: () => void
}

export const NotificationSettingsCard: React.FC<NotificationSettingsCardProps> = ({
  notifications,
  onToggle,
  onManageClick,
}) => {
  const items: Array<{ key: keyof NotificationSettingsData; title: string; desc: string; icon: React.ReactNode }> = [
    { key: 'workoutReminders', title: 'Workout Reminders', desc: 'Get reminded about your workouts', icon: <Dumbbell className="h-4 w-4 text-blue-400" /> },
    { key: 'restTimerAlerts', title: 'Rest Timer Alerts', desc: 'Alerts for rest time completion', icon: <Timer className="h-4 w-4 text-amber-400" /> },
    { key: 'achievementNotifications', title: 'Achievement Notifications', desc: 'Celebrate your achievements', icon: <Trophy className="h-4 w-4 text-purple-400" /> },
    { key: 'nutritionReminders', title: 'Nutrition Reminders', desc: 'Stay on track with your nutrition', icon: <Apple className="h-4 w-4 text-emerald-400" /> },
    { key: 'aiCoachInsights', title: 'AI Coach Insights', desc: 'Get AI-powered fitness insights', icon: <Bot className="h-4 w-4 text-cyan-400" /> },
    { key: 'weeklyProgressReport', title: 'Weekly Progress Report', desc: 'Summary of your weekly progress', icon: <BarChart2 className="h-4 w-4 text-amber-400" /> },
  ]

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Bell className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-100">Notification Center</h3>
        </div>

        <div className="space-y-2 font-mono text-xs">
          {items.map((item) => {
            const enabled = notifications[item.key]

            return (
              <div
                key={item.key}
                className="flex items-center justify-between p-2 rounded-2xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 shrink-0">
                    {item.icon}
                  </div>
                  <div className="space-y-0.5 font-sans">
                    <h4 className="text-xs font-bold text-slate-100">{item.title}</h4>
                    <p className="text-[10px] text-slate-400">{item.desc}</p>
                  </div>
                </div>

                {/* Pill Toggle Switch */}
                <button
                  type="button"
                  onClick={() => onToggle(item.key)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    enabled ? 'bg-emerald-500' : 'bg-slate-800'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ease-in-out ${
                      enabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onManageClick}
          className="flex items-center justify-between w-full text-xs font-mono text-emerald-400 hover:text-emerald-300 font-bold transition-colors"
        >
          <span>Manage All Notifications</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
