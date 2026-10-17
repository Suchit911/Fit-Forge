import React, { useState } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check } from 'lucide-react'
import type { PersonalInformationData } from '../../types'

export interface EditProfileModalProps {
  isOpen: boolean
  onClose: () => void
  currentInfo?: PersonalInformationData
  name?: string
  onSave: (data: { name: string; age: number; heightCm: number; weightKg: number; fitnessGoal: string; activityLevel: string }) => void
}

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  isOpen,
  onClose,
  currentInfo,
  name = '',
  onSave,
}) => {
  const [fullName, setFullName] = useState(name)
  const [age, setAge] = useState(currentInfo?.age ? String(currentInfo.age) : '')
  const [height, setHeight] = useState(currentInfo?.heightCm ? String(currentInfo.heightCm) : '')
  const [weight, setWeight] = useState(currentInfo?.weightKg ? String(currentInfo.weightKg) : '')
  const [fitnessGoal, setFitnessGoal] = useState(currentInfo?.fitnessGoal || 'General Fitness')
  const [activityLevel, setActivityLevel] = useState(currentInfo?.activityLevel || 'Intermediate')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name: fullName,
      age: Number(age) || 0,
      heightCm: Number(height) || 0,
      weightKg: Number(weight) || 0,
      fitnessGoal,
      activityLevel,
    })
    setSubmitted(true)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Personal Profile">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Profile Updated!</h4>
            <p className="text-xs text-slate-400">Your changes have been saved successfully.</p>
          </div>
        ) : (
          <>
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />

            <div className="grid grid-cols-3 gap-3">
              <Input label="Age" type="number" value={age} onChange={(e) => setAge(e.target.value)} />
              <Input label="Height (cm)" type="number" value={height} onChange={(e) => setHeight(e.target.value)} />
              <Input label="Weight (kg)" type="number" value={weight} onChange={(e) => setWeight(e.target.value)} />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Fitness Goal</label>
              <select
                value={fitnessGoal}
                onChange={(e) => setFitnessGoal(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="Build Muscle">Build Muscle</option>
                <option value="Fat Loss">Fat Loss</option>
                <option value="Increase Strength">Increase Strength</option>
                <option value="General Fitness">General Fitness</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Activity Level</label>
              <select
                value={activityLevel}
                onChange={(e) => setActivityLevel(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="Lightly Active">Lightly Active (1-2 days/wk)</option>
                <option value="Moderately Active">Moderately Active (3-4 days/wk)</option>
                <option value="Very Active">Very Active (5-6 days/wk)</option>
                <option value="Extremely Active">Extremely Active (Athlete)</option>
              </select>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" variant="primary" className="flex-1">
                Save Changes
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
