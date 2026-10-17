import React, { useState } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check } from 'lucide-react'
import { useAchievements } from '../../hooks'

export interface AchievementAddModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export const AchievementAddModal: React.FC<AchievementAddModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { addAchievement, isAdding } = useAchievements()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('Workout Mastery')
  const [submitted, setSubmitted] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    try {
      setErrorMsg(null)
      await addAchievement({ name: name.trim(), description: description.trim(), category })
      setSubmitted(true)
      setTimeout(() => {
        onSuccess()
        setSubmitted(false)
        setName('')
        setDescription('')
        onClose()
      }, 600)
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to record custom milestone. Please try again.')
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Custom Achievement">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Achievement Added!</h4>
            <p className="text-xs text-slate-400">Your new milestone has been recorded.</p>
          </div>
        ) : (
          <>
            {errorMsg && (
              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-sans">
                {errorMsg}
              </div>
            )}

            <Input
              label="Achievement Name"
              placeholder="e.g. 100kg Bench Milestone"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Description</label>
              <textarea
                rows={3}
                placeholder="e.g. Successfully benched 100kg for 3 clean reps."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-200 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="Workout Mastery">Workout Mastery</option>
                <option value="Strength">Strength</option>
                <option value="Endurance">Endurance</option>
                <option value="Consistency">Consistency</option>
                <option value="Nutrition">Nutrition</option>
                <option value="Special">Special</option>
              </select>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1" disabled={isAdding}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" className="flex-1" disabled={isAdding}>
                {isAdding ? 'Saving...' : 'Save Achievement'}
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
