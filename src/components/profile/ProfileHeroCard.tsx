import React from 'react'
import type { ProfileHeroStats } from '../../types'
import { Camera, CheckCircle2, Crown, Calendar, MapPin, Flame, Dumbbell, Star, User as UserIcon } from 'lucide-react'

export interface ProfileHeroCardProps {
  hero: ProfileHeroStats
  onEditAvatarClick: () => void
}

export const ProfileHeroCard: React.FC<ProfileHeroCardProps> = ({ hero, onEditAvatarClick }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl text-left">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        
        {/* Left Section: Avatar & Details (5 of 12 cols) */}
        <div className="lg:col-span-5 flex items-center gap-5">
          {/* Avatar with Camera Button */}
          <div className="relative shrink-0">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-tr from-emerald-500 to-cyan-500 text-slate-950 font-extrabold text-2xl border-2 border-emerald-400 shadow-xl overflow-hidden">
              <UserIcon className="h-10 w-10 text-slate-950" />
            </div>
            <button
              type="button"
              onClick={onEditAvatarClick}
              aria-label="Edit avatar"
              className="absolute bottom-0 right-0 flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 text-slate-950 border-2 border-slate-900 hover:bg-emerald-400 transition-colors shadow-md cursor-pointer"
            >
              <Camera className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Identity & Badges */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-extrabold text-slate-100">{hero.name}</h2>
              {hero.verified && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
            </div>

            <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-950/80 border border-purple-500/40 text-purple-300 font-mono text-[10px] font-bold">
              <Crown className="h-3 w-3 text-purple-400" /> {hero.plan}
            </div>

            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-400">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3 text-emerald-400" /> Member since {hero.memberSince}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3 text-emerald-400" /> {hero.location}
              </span>
            </div>

            <p className="text-xs text-slate-300 italic font-medium pt-0.5">
              {hero.quote}
            </p>
          </div>
        </div>

        {/* Center Section: Anatomical Body Graphic (3 of 12 cols) */}
        <div className="lg:col-span-3 flex justify-center border-t lg:border-t-0 lg:border-l border-slate-800/80 pt-4 lg:pt-0 lg:px-4">
          <svg className="h-28 w-20 text-emerald-500/40" viewBox="0 0 100 150" fill="none">
            <circle cx="50" cy="18" r="10" stroke="#10b981" strokeWidth="2" fill="#064e3b" fillOpacity="0.2" />
            <path d="M32 35 L 68 35 L 62 85 L 38 85 Z" stroke="#10b981" strokeWidth="2" fill="#064e3b" fillOpacity="0.2" />
            <path d="M30 35 L 18 80 M 70 35 L 82 80" stroke="#10b981" strokeWidth="2.5" />
            <path d="M42 85 L 38 140 M 58 85 L 62 140" stroke="#10b981" strokeWidth="3" />
            <path d="M35 40 Q 50 48, 65 40 L 62 58 Q 50 64, 38 58 Z" fill="#10b981" fillOpacity="0.3" stroke="#34d399" strokeWidth="1.5" />
          </svg>
        </div>

        {/* Right Section: 4 Compact Metrics (4 of 12 cols) */}
        <div className="lg:col-span-4 grid grid-cols-2 gap-4 border-t lg:border-t-0 lg:border-l border-slate-800/80 pt-4 lg:pt-0 lg:pl-6 font-mono">
          
          {/* Current Streak */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Flame className="h-3.5 w-3.5" />
              </div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Current Streak</span>
            </div>
            <span className="text-lg font-extrabold text-slate-100 block">{hero.streakDays} Days</span>
            <span className="text-[9px] text-emerald-400 font-bold block">Keep it going!</span>
          </div>

          {/* Total Workouts */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Dumbbell className="h-3.5 w-3.5" />
              </div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Total Workouts</span>
            </div>
            <span className="text-lg font-extrabold text-slate-100 block">{hero.totalWorkouts}</span>
            <span className="text-[9px] text-slate-400 font-bold block">This Year</span>
          </div>

          {/* Total Calories */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Flame className="h-3.5 w-3.5" />
              </div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Total Calories</span>
            </div>
            <span className="text-lg font-extrabold text-slate-100 block">{hero.totalCaloriesBurned.toLocaleString()}</span>
            <span className="text-[9px] text-slate-400 font-bold block">kcal Burned</span>
          </div>

          {/* Total Points */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Star className="h-3.5 w-3.5" />
              </div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Total Points</span>
            </div>
            <span className="text-lg font-extrabold text-slate-100 block">{hero.totalPoints.toLocaleString()}</span>
            <span className="text-[9px] text-purple-400 font-bold block">{hero.rankPct}</span>
          </div>

        </div>

      </div>
    </div>
  )
}
