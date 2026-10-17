import React, { useState } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check } from 'lucide-react'

export interface CreateCustomExerciseModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (newEx: any) => void
}

export const CreateCustomExerciseModal: React.FC<CreateCustomExerciseModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState('')
  const [primaryMuscle, setPrimaryMuscle] = useState('chest')
  const [equipment, setEquipment] = useState('dumbbells')
  const [difficulty, setDifficulty] = useState('intermediate')
  const [description, setDescription] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    const newEx = {
      id: `ex_custom_${Date.now()}`,
      name,
      description: description || 'Custom user defined exercise.',
      primaryMuscles: [primaryMuscle],
      secondaryMuscles: [],
      equipment: [equipment],
      difficulty,
      category: 'custom',
      instructions: ['Perform exercise according to personal technique.'],
      commonMistakes: [],
      safetyNotes: [],
      supportedFormAnalysis: false,
    }

    setSubmitted(true)
    setTimeout(() => {
      onSuccess(newEx)
      setSubmitted(false)
      setName('')
      setDescription('')
      onClose()
    }, 600)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Custom Exercise">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Exercise Created!</h4>
            <p className="text-xs text-slate-400">Added to your local exercise library.</p>
          </div>
        ) : (
          <>
            <Input
              label="Exercise Name"
              placeholder="e.g. Incline Cable Fly"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-slate-300 font-bold block">Primary Muscle</label>
                <select
                  value={primaryMuscle}
                  onChange={(e) => setPrimaryMuscle(e.target.value)}
                  className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="chest">Chest</option>
                  <option value="back">Back</option>
                  <option value="shoulders">Shoulders</option>
                  <option value="biceps">Biceps</option>
                  <option value="triceps">Triceps</option>
                  <option value="quadriceps">Legs</option>
                  <option value="core">Core</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-bold block">Equipment</label>
                <select
                  value={equipment}
                  onChange={(e) => setEquipment(e.target.value)}
                  className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="barbell">Barbell</option>
                  <option value="dumbbells">Dumbbells</option>
                  <option value="cable_machine">Cable Machine</option>
                  <option value="bodyweight">Bodyweight</option>
                  <option value="kettlebell">Kettlebell</option>
                </select>
              </div>
            </div>

            <div className="space-y-1 text-xs font-mono">
              <label className="text-slate-300 font-bold block">Difficulty Level</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div className="space-y-1 text-xs">
              <label className="text-slate-300 font-bold block font-mono">Description / Notes</label>
              <textarea
                rows={3}
                placeholder="Key execution cues or description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" variant="primary" className="flex-1">
                Create Exercise
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
