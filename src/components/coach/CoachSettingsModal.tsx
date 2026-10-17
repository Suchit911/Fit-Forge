import React, { useState } from 'react'
import { Modal, Button } from '../ui'
import { Check } from 'lucide-react'

export interface CoachSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export const CoachSettingsModal: React.FC<CoachSettingsModalProps> = ({ isOpen, onClose }) => {
  const [tone, setTone] = useState('encouraging')
  const [focusArea, setFocusArea] = useState('hypertrophy')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    setTimeout(() => {
      setSubmitted(false)
      onClose()
    }, 600)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="AI Coach Settings">
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Settings Saved!</h4>
            <p className="text-xs text-slate-400">Your AI Coach preferences have been updated.</p>
          </div>
        ) : (
          <>
            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Coaching Persona / Tone</label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="encouraging">Encouraging & Supportive</option>
                <option value="strict">Strict & Disciplined</option>
                <option value="scientific">Scientific & Data-Driven</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-bold block">Primary AI Focus</label>
              <select
                value={focusArea}
                onChange={(e) => setFocusArea(e.target.value)}
                className="w-full h-9 rounded-xl border border-slate-800 bg-slate-950 px-3 text-xs text-slate-200 focus:outline-none"
              >
                <option value="hypertrophy">Muscle Gain / Hypertrophy</option>
                <option value="fat_loss">Fat Loss / Conditioning</option>
                <option value="strength">Maximum Strength</option>
                <option value="recovery">Recovery & Injury Prevention</option>
              </select>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" variant="primary" className="flex-1">
                Save Preferences
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
