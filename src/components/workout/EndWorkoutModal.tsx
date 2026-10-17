import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal, Button } from '../ui'
import { AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'

export interface EndWorkoutModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirmEnd?: () => Promise<void> | void
  isCompleting?: boolean
  completedSetsCount?: number
  totalSetsCount?: number
  completedCount?: number
  totalCount?: number
  errorMessage?: string | null
}

export const EndWorkoutModal: React.FC<EndWorkoutModalProps> = ({
  isOpen,
  onClose,
  onConfirmEnd,
  isCompleting = false,
  completedSetsCount,
  totalSetsCount,
  completedCount = 1,
  totalCount = 6,
  errorMessage,
}) => {
  const navigate = useNavigate()

  const compSets = completedSetsCount ?? completedCount
  const totSets = totalSetsCount ?? totalCount
  const isAllCompleted = totSets > 0 && compSets >= totSets

  const handleEndWorkout = async () => {
    if (onConfirmEnd) {
      await onConfirmEnd()
    } else {
      onClose()
      navigate('/workouts')
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isAllCompleted ? 'Complete Workout?' : 'End Workout Early?'}
    >
      <div className="space-y-4 text-left pt-1">
        {errorMessage && (
          <div className="p-3 rounded-xl border border-red-500/50 bg-red-950/40 text-red-200 text-xs font-mono">
            {errorMessage}
          </div>
        )}

        <div
          className={`flex items-center gap-3 p-3 rounded-xl border text-xs ${
            isAllCompleted
              ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
              : 'bg-amber-950/30 border-amber-500/30 text-amber-300'
          }`}
        >
          {isAllCompleted ? (
            <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
          )}
          <span>
            {isAllCompleted
              ? `Great job! You've completed all ${totSets} sets. Ready to log your session and update your progress?`
              : `You've completed ${compSets} of ${totSets} planned sets. Are you sure you want to end this workout session now?`}
          </span>
        </div>

        <div className="flex gap-3 pt-2">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isCompleting}
            className="flex-1"
          >
            Continue Workout
          </Button>
          <Button
            variant={isAllCompleted ? 'primary' : 'danger'}
            onClick={handleEndWorkout}
            disabled={isCompleting}
            className="flex-1 flex items-center justify-center gap-2"
          >
            {isCompleting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Completing...</span>
              </>
            ) : (
              <span>{isAllCompleted ? 'Complete & Save' : 'End Workout'}</span>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
