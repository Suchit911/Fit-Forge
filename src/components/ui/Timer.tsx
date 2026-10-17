import React, { useEffect, useState } from 'react'
import { formatDuration, cn } from '../../lib/utils'

export interface TimerProps {
  initialSeconds?: number
  isCountingDown?: boolean
  autoStart?: boolean
  onComplete?: () => void
  className?: string
}

export const Timer: React.FC<TimerProps> = ({
  initialSeconds = 60,
  isCountingDown = true,
  autoStart = false,
  onComplete,
  className,
}) => {
  const [seconds, setSeconds] = useState(initialSeconds)
  const [isRunning, setIsRunning] = useState(autoStart)

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null
    if (isRunning) {
      interval = setInterval(() => {
        setSeconds((prev) => {
          if (isCountingDown) {
            if (prev <= 1) {
              setIsRunning(false)
              if (onComplete) onComplete()
              return 0
            }
            return prev - 1
          } else {
            return prev + 1
          }
        })
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isRunning, isCountingDown, onComplete])

  return (
    <div className={cn('inline-flex items-center gap-2 font-mono font-bold text-slate-100', className)}>
      <span className="text-xl tracking-wider">{formatDuration(seconds)}</span>
      <button
        type="button"
        onClick={() => setIsRunning(!isRunning)}
        className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-sans cursor-pointer transition-colors"
      >
        {isRunning ? 'Pause' : 'Start'}
      </button>
    </div>
  )
}
