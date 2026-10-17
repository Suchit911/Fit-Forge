import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from './Button'
import { cn } from '../../lib/utils'

export interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  className?: string
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'Failed to load domain data. Please try again.',
  onRetry,
  className,
}) => {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-red-900/40 bg-red-950/20 p-6 sm:p-8 text-center',
        className
      )}
    >
      <div className="mb-4 rounded-full bg-red-900/30 p-3 text-red-400" aria-hidden="true">
        <AlertTriangle className="h-8 w-8" aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-red-200 break-words">{title}</h3>
      <p className="mt-1 text-xs text-red-300/80 max-w-md break-words leading-relaxed">{message}</p>
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          size="md"
          className="mt-4 border-red-800 text-red-200 hover:bg-red-900/40"
        >
          <RefreshCw className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
          Retry Request
        </Button>
      )}
    </div>
  )
}
