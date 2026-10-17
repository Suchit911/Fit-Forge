import React from 'react'
import type { PrivacySettingsData } from '../../types'
import { Shield, User, Database, Camera, Bot, Lock, ShieldCheck, Download, ChevronRight } from 'lucide-react'

export interface PrivacySecurityCardProps {
  privacy: PrivacySettingsData
  onToggleAi: () => void
  onUpdate: (data: Partial<PrivacySettingsData>) => void
  onActionClick: (act: string) => void
}

export const PrivacySecurityCard: React.FC<PrivacySecurityCardProps> = ({
  privacy,
  onToggleAi,
  onUpdate,
  onActionClick,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Shield className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Privacy & Security</h3>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {/* Profile Visibility */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Profile Visibility</span>
          </div>
          <select
            value={privacy.profileVisibility}
            onChange={(e) => onUpdate({ profileVisibility: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer"
          >
            <option value="Public">Public</option>
            <option value="Friends Only">Friends Only</option>
            <option value="Private">Private</option>
          </select>
        </div>

        {/* Workout Data */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Workout Data</span>
          </div>
          <select
            value={privacy.workoutDataVisibility}
            onChange={(e) => onUpdate({ workoutDataVisibility: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer max-w-[150px] truncate"
          >
            <option value="Only You">Visible to: Only You</option>
            <option value="Friends">Visible to: Friends</option>
            <option value="Public">Visible to: Public</option>
          </select>
        </div>

        {/* Progress Photos */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Progress Photos</span>
          </div>
          <select
            value={privacy.progressPhotosVisibility}
            onChange={(e) => onUpdate({ progressPhotosVisibility: e.target.value })}
            className="rounded-xl border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-100 font-bold focus:outline-none cursor-pointer max-w-[150px] truncate"
          >
            <option value="Only You">Visible to: Only You</option>
            <option value="Private">Visible to: Private</option>
          </select>
        </div>

        {/* AI Analysis Data */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-emerald-400" />
            <div>
              <span className="text-slate-300 font-bold block">AI Analysis Data</span>
              <span className="text-[10px] text-slate-400 font-sans">Used to improve AI</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onToggleAi}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
              privacy.aiAnalysisData ? 'bg-emerald-500' : 'bg-slate-800'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ${
                privacy.aiAnalysisData ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Change Password */}
        <button
          type="button"
          onClick={() => onActionClick('Change Password')}
          className="flex items-center justify-between w-full py-1 border-b border-slate-800/50 text-left hover:text-emerald-400 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Change Password</span>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-500" />
        </button>

        {/* Two-Factor Authentication */}
        <button
          type="button"
          onClick={() => onActionClick('Two-Factor Authentication')}
          className="flex items-center justify-between w-full py-1 border-b border-slate-800/50 text-left hover:text-emerald-400 transition-colors"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-bold">Two-Factor Authentication</span>
          </div>
          <span className="text-emerald-400 font-bold flex items-center gap-1">
            Enabled <ChevronRight className="h-4 w-4 text-slate-500" />
          </span>
        </button>

        {/* Manage Data */}
        <button
          type="button"
          onClick={() => onActionClick('Manage Data')}
          className="flex items-center justify-between w-full py-1 text-left hover:text-emerald-400 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Download className="h-4 w-4 text-emerald-400" />
            <div>
              <span className="text-slate-300 font-bold block">Manage Data</span>
              <span className="text-[10px] text-slate-400 font-sans">Download or delete</span>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-500" />
        </button>
      </div>
    </div>
  )
}
