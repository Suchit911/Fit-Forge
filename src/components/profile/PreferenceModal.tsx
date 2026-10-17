import React, { useState } from 'react'
import { Modal, Button } from '../ui'
import { Check } from 'lucide-react'

export interface PreferenceModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
}

export const PreferenceModal: React.FC<PreferenceModalProps> = ({ isOpen, onClose, title }) => {
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Preferences Saved!</h4>
            <p className="text-xs text-slate-400">Your configuration has been updated.</p>
          </div>
        ) : (
          <>
            <p className="text-slate-300">
              Adjust your preference settings to personalize your training and nutrition recommendations.
            </p>

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
