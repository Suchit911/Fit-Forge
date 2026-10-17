import React from 'react'
import type { PersonalInformationData } from '../../types'
import { User, Ruler, Scale, Target, Zap } from 'lucide-react'

export interface PersonalInformationCardProps {
  info: PersonalInformationData
}

export const PersonalInformationCard: React.FC<PersonalInformationCardProps> = ({ info }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Personal Information
      </h3>

      <div className="space-y-3 font-mono text-xs">
        {/* Age */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Age</span>
          </div>
          <span className="font-extrabold text-slate-100">{info.age && info.age > 0 ? `${info.age} years` : 'Not set'}</span>
        </div>

        {/* Height */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Ruler className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Height</span>
          </div>
          <span className="font-extrabold text-slate-100">{info.heightCm && info.heightCm > 0 ? `${info.heightCm} cm` : 'Not set'}</span>
        </div>

        {/* Weight */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Weight</span>
          </div>
          <span className="font-extrabold text-slate-100">{info.weightKg && info.weightKg > 0 ? `${info.weightKg} kg` : 'Not set'}</span>
        </div>

        {/* Fitness Goal */}
        <div className="flex items-center justify-between py-1 border-b border-slate-800/50">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Fitness Goal</span>
          </div>
          <span className="font-extrabold text-emerald-400">{info.fitnessGoal}</span>
        </div>

        {/* Activity Level */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400 font-bold">Activity Level</span>
          </div>
          <span className="font-extrabold text-slate-100">{info.activityLevel}</span>
        </div>
      </div>
    </div>
  )
}
