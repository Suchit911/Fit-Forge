import React from 'react'
import { Search, ChevronDown, SlidersHorizontal } from 'lucide-react'

export interface ExerciseSearchBarProps {
  searchQuery: string
  onSearchChange: (q: string) => void
  selectedMuscle: string
  onMuscleChange: (m: string) => void
  selectedEquipment: string
  onEquipmentChange: (e: string) => void
  selectedDifficulty: string
  onDifficultyChange: (d: string) => void
  sortBy: string
  onSortChange: (s: string) => void
}

export const ExerciseSearchBar: React.FC<ExerciseSearchBarProps> = ({
  searchQuery,
  onSearchChange,
  selectedMuscle,
  onMuscleChange,
  selectedEquipment,
  onEquipmentChange,
  selectedDifficulty,
  onDifficultyChange,
  sortBy,
  onSortChange,
}) => {
  return (
    <div className="space-y-4 text-left">
      {/* Large Search Input */}
      <div className="relative w-full">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search exercises by name, muscle group, or equipment..."
          className="w-full h-12 rounded-2xl border border-slate-800 bg-slate-900/90 pl-11 pr-16 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors shadow-lg"
        />
        <kbd className="absolute right-4 top-1/2 -translate-y-1/2 rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-400 border border-slate-700">
          ⌘ K
        </kbd>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2">
          {/* All Exercises Pill */}
          <div className="relative">
            <select
              value={selectedMuscle}
              onChange={(e) => onMuscleChange(e.target.value)}
              className="appearance-none rounded-xl border border-emerald-500/40 bg-emerald-950/60 pl-3 pr-8 py-2 text-xs font-bold text-emerald-400 focus:outline-none cursor-pointer"
            >
              <option value="All">All Exercises</option>
              <option value="chest">Chest</option>
              <option value="back">Back</option>
              <option value="shoulders">Shoulders</option>
              <option value="arms">Arms</option>
              <option value="quadriceps">Legs</option>
              <option value="core">Core</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-emerald-400 pointer-events-none" />
          </div>

          {/* Muscle Group Dropdown */}
          <div className="relative">
            <select
              value={selectedMuscle}
              onChange={(e) => onMuscleChange(e.target.value)}
              className="appearance-none rounded-xl border border-slate-800 bg-slate-900/90 pl-3 pr-8 py-2 text-xs font-semibold text-slate-300 focus:outline-none hover:border-slate-700 cursor-pointer"
            >
              <option value="All">Muscle Group</option>
              <option value="chest">Chest</option>
              <option value="back">Back</option>
              <option value="shoulders">Shoulders</option>
              <option value="quadriceps">Legs</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500 pointer-events-none" />
          </div>

          {/* Equipment Dropdown */}
          <div className="relative">
            <select
              value={selectedEquipment}
              onChange={(e) => onEquipmentChange(e.target.value)}
              className="appearance-none rounded-xl border border-slate-800 bg-slate-900/90 pl-3 pr-8 py-2 text-xs font-semibold text-slate-300 focus:outline-none hover:border-slate-700 cursor-pointer"
            >
              <option value="All">Equipment</option>
              <option value="barbell">Barbell</option>
              <option value="dumbbells">Dumbbells</option>
              <option value="cable_machine">Cable Machine</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500 pointer-events-none" />
          </div>

          {/* Difficulty Dropdown */}
          <div className="relative">
            <select
              value={selectedDifficulty}
              onChange={(e) => onDifficultyChange(e.target.value)}
              className="appearance-none rounded-xl border border-slate-800 bg-slate-900/90 pl-3 pr-8 py-2 text-xs font-semibold text-slate-300 focus:outline-none hover:border-slate-700 cursor-pointer"
            >
              <option value="All">Difficulty</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500 pointer-events-none" />
          </div>

          {/* Exercise Type */}
          <button
            type="button"
            className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-700 cursor-pointer"
          >
            <span>Exercise Type</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          </button>

          {/* More Filters */}
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-700 cursor-pointer"
          >
            <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
            <span>More Filters</span>
          </button>
        </div>

        {/* Sort By Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-xs">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs font-semibold text-slate-200 focus:outline-none cursor-pointer"
          >
            <option value="popular">Popular</option>
            <option value="rating">Highest Rated</option>
            <option value="name">Name (A-Z)</option>
          </select>
        </div>
      </div>
    </div>
  )
}
