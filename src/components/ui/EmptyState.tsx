import React from 'react'
import { FolderOpen } from 'lucide-react'
import { Button } from './Button'
import { cn } from '../../lib/utils'

export interface EmptyStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No data found',
  description = 'There are currently no items to display.',
  actionLabel,
  onAction,
  icon = <FolderOpen className="h-10 w-10 text-slate-500" aria-hidden="true" />,
  className,
}) => {
  return (
    <div
      role="region"
      aria-label={title}
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 p-6 sm:p-8 text-center bg-slate-900/30',
        className
      )}
    >
      <div className="mb-4 rounded-full bg-slate-800/60 p-4" aria-hidden="true">{icon}</div>
      <h3 className="text-base font-semibold text-slate-200 break-words">{title}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm break-words leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} size="md" className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
