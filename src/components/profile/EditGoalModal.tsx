import React, { useState } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check } from 'lucide-react'
import type { FitnessGoalData } from '../../types'

export interface EditGoalModalProps {
  isOpen: boolean
  onClose: () => void
  currentGoal?: FitnessGoalData
  onSave: (data: { primaryGoal: string; targetWeightKg: number; weeklyTarget: string; targetDate: string }) => void
}

export const EditGoalModal: React.FC<EditGoalModalProps> = ({
  isOpen,
  onClose,
  currentGoal,
  onSave,
}) => {
  const [primaryGoal, setPrimaryGoal] = useState(currentGoal?.primaryGoal || 'General Fitness')
  const [targetWeight, setTargetWeight] = useState(currentGoal?.targetWeightKg ? String(currentGoal.targetWeightKg) : '')
  const [weeklyTarget, setWeeklyTarget] = useState(currentGoal?.weeklyWorkoutTarget || '')
  const [targetDate, setTargetDate] = useState(currentGoal?.targetDate || '')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      primaryGoal,
      targetWeightKg: Number(targetWeight) || 0,
      weeklyTarget,
      targetDate,
    })
    setSubmitted(true)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Fitness Goal">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Goals Updated!</h4>
            <p className="text-xs text-slate-400">Your targets have been saved successfully.</p>
          </div>
        ) : (
          <>
            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Primary Goal</label>
              <select
                value={primaryGoal}
                onChange={(e) => setPrimaryGoal(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="Build Muscle">Build Muscle</option>
                <option value="Fat Loss & Toning">Fat Loss & Toning</option>
                <option value="Strength Powerlifting">Strength Powerlifting</option>
                <option value="Marathon Endurance">Marathon Endurance</option>
              </select>
            </div>

            <Input
              label="Target Weight (kg)"
              type="number"
              value={targetWeight}
              onChange={(e) => setTargetWeight(e.target.value)}
            />

            <Input
              label="Weekly Workout Target"
              placeholder="e.g. 4 - 5 days"
              value={weeklyTarget}
              onChange={(e) => setWeeklyTarget(e.target.value)}
            />

            <Input
              label="Target Deadline Date"
              placeholder="e.g. Dec 31, 2025"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" variant="primary" className="flex-1">
                Save Goal
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
