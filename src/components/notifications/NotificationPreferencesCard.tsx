import React, { useState } from 'react'
import { Sliders, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export interface NotificationPreferencesCardProps {
  initialPrefs?: Record<string, boolean>
}

export const NotificationPreferencesCard: React.FC<NotificationPreferencesCardProps> = ({ initialPrefs }) => {
  const navigate = useNavigate()

  const [prefs, setPrefs] = useState<Record<string, boolean>>(
    initialPrefs || {
      workoutReminders: true,
      achievementAlerts: true,
      nutritionReminders: true,
      aiCoachInsights: true,
      progressReports: true,
      marketingPromotions: false,
    }
  )

  const items: Array<{ key: string; label: string }> = [
    { key: 'workoutReminders', label: 'Workout Reminders' },
    { key: 'achievementAlerts', label: 'Achievement Alerts' },
    { key: 'nutritionReminders', label: 'Nutrition Reminders' },
    { key: 'aiCoachInsights', label: 'AI Coach Insights' },
    { key: 'progressReports', label: 'Progress Reports' },
    { key: 'marketingPromotions', label: 'Marketing & Promotions' },
  ]

  const toggle = (key: string) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Sliders className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Notification Preferences</h3>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {items.map((item) => {
          const enabled = prefs[item.key]

          return (
            <div
              key={item.key}
              className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800"
            >
              <span className="font-bold text-slate-300">{item.label}</span>

              {/* Pill Toggle */}
              <button
                type="button"
                onClick={() => toggle(item.key)}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                  enabled ? 'bg-emerald-500' : 'bg-slate-800'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ${
                    enabled ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          )
        })}
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className="flex items-center justify-between w-full text-xs font-mono text-emerald-400 hover:text-emerald-300 font-bold transition-colors cursor-pointer"
        >
          <span>Manage Notification Settings</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
