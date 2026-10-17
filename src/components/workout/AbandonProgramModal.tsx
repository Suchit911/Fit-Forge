import React from 'react'
import { Modal, Button } from '../ui'
import { AlertTriangle, ShieldCheck } from 'lucide-react'

export interface AbandonProgramModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirmAbandon: () => Promise<void> | void
  isAbandoning?: boolean
  errorMessage?: string | null
}

export const AbandonProgramModal: React.FC<AbandonProgramModalProps> = ({
  isOpen,
  onClose,
  onConfirmAbandon,
  isAbandoning = false,
  errorMessage,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Abandon Active Program?"
      description="Conclude tracking for your current active mesocycle."
    >
      <div className="space-y-4 text-left pt-1">
        {errorMessage && (
          <div
            role="alert"
            className="p-3 rounded-xl border border-red-500/50 bg-red-950/40 text-red-200 text-xs font-mono break-words"
          >
            {errorMessage}
          </div>
        )}

        <div className="flex items-start gap-3 p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/20 text-xs text-amber-200/90 leading-relaxed min-w-0">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="min-w-0">
            <p className="font-semibold text-amber-300 mb-1">
              Active Program Lifecycle Notice
            </p>
            <p className="break-words">
              Abandoning this program will conclude tracking for your current mesocycle. The program will no longer appear as your active routine, and today's prescription will no longer be active.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-800 bg-slate-950/60 text-xs text-slate-300 min-w-0">
          <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" aria-hidden="true" />
          <span className="break-words">
            All your logged workouts, completed set data, and adaptation history will remain securely preserved in your training history.
          </span>
        </div>

        <div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isAbandoning}
            className="w-full sm:flex-1 min-h-[44px]"
          >
            Keep Program
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirmAbandon}
            isLoading={isAbandoning}
            disabled={isAbandoning}
            className="w-full sm:flex-1 min-h-[44px]"
            id="confirm-abandon-program-btn"
          >
            Abandon Program
          </Button>
        </div>
      </div>
    </Modal>
  )
}
