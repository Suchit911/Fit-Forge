import React, { useState } from 'react'
import { Modal, Button } from '../ui'
import { Check, AlertTriangle } from 'lucide-react'

export interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  description: string
  confirmText?: string
  isDanger?: boolean
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  confirmText = 'Confirm',
  isDanger = false,
}) => {
  const [submitted, setSubmitted] = useState(false)

  const handleConfirm = () => {
    setSubmitted(true)
    setTimeout(() => {
      setSubmitted(false)
      onClose()
    }, 600)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4 text-left pt-1 font-mono text-xs">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Action Executed</h4>
            <p className="text-xs text-slate-400">Settings action completed successfully.</p>
          </div>
        ) : (
          <>
            <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-950 border border-slate-800">
              {isDanger && <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />}
              <p className="text-slate-300 font-sans leading-relaxed">{description}</p>
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button
                type="button"
                variant={isDanger ? 'outline' : 'primary'}
                onClick={handleConfirm}
                className={`flex-1 ${isDanger ? 'border-rose-500 text-rose-400 hover:bg-rose-500 hover:text-slate-950' : ''}`}
              >
                {confirmText}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
