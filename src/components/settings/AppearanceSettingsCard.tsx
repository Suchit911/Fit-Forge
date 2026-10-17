import React from 'react'
import type { AppearanceSettingsData } from '../../types'
import { Palette, Moon, Droplets, Sliders, Layout, Sparkles, EyeOff, ChevronRight } from 'lucide-react'

export interface AppearanceSettingsCardProps {
  appearance: AppearanceSettingsData
  onToggle: (key: keyof AppearanceSettingsData) => void
  onUpdate: (data: Partial<AppearanceSettingsData>) => void
  onPreviewClick: () => void
}

export const AppearanceSettingsCard: React.FC<AppearanceSettingsCardProps> = ({
  appearance,
  onToggle,
  onUpdate,
  onPreviewClick,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Palette className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-100">Appearance</h3>
        </div>

        <div className="space-y-2.5 font-mono text-xs">
          {/* Dark Mode */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Moon className="h-4 w-4 text-purple-400" />
              <div>
                <span className="text-slate-300 font-bold block">Dark Mode</span>
                <span className="text-[10px] text-slate-400 font-sans">Enable dark theme</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onToggle('darkMode')}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                appearance.darkMode ? 'bg-emerald-500' : 'bg-slate-800'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ${
                  appearance.darkMode ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Accent Color */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Droplets className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Accent Color</span>
            </div>
            <div className="flex items-center gap-1.5 font-bold text-slate-100">
              <span>{appearance.accentColor}</span>
              <span className="h-3 w-3 rounded-full bg-emerald-500" />
            </div>
          </div>

          {/* Accent Intensity */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">Accent Intensity</span>
            </div>
            <select
              value={appearance.accentIntensity}
              onChange={(e) => onUpdate({ accentIntensity: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>

          {/* UI Density */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Layout className="h-4 w-4 text-purple-400" />
              <span className="text-slate-300 font-bold">UI Density</span>
            </div>
            <select
              value={appearance.uiDensity}
              onChange={(e) => onUpdate({ uiDensity: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
            >
              <option value="Compact">Compact</option>
              <option value="Comfortable">Comfortable</option>
              <option value="Spacious">Spacious</option>
            </select>
          </div>

          {/* Animations */}
          <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <div>
                <span className="text-slate-300 font-bold block">Animations</span>
                <span className="text-[10px] text-slate-400 font-sans">Enable UI animations</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onToggle('animations')}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                appearance.animations ? 'bg-emerald-500' : 'bg-slate-800'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ${
                  appearance.animations ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Reduce Motion */}
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <EyeOff className="h-4 w-4 text-purple-400" />
              <div>
                <span className="text-slate-300 font-bold block">Reduce Motion</span>
                <span className="text-[10px] text-slate-400 font-sans">Minimize animations</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onToggle('reduceMotion')}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                appearance.reduceMotion ? 'bg-emerald-500' : 'bg-slate-800'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ${
                  appearance.reduceMotion ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onPreviewClick}
          className="flex items-center justify-between w-full text-xs font-mono text-purple-400 hover:text-purple-300 font-bold transition-colors"
        >
          <span>Preview Changes</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
