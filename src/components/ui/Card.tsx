import React from 'react'
import { cn } from '../../lib/utils'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'ghost'
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variants = {
      default: 'bg-slate-900/80 border border-slate-800 shadow-md text-slate-100',
      outline: 'bg-transparent border border-slate-800 text-slate-100',
      ghost: 'bg-slate-900/40 text-slate-100',
    }

    return (
      <div
        ref={ref}
        className={cn('rounded-xl p-5 transition-all', variants[variant], className)}
        {...props}
      />
    )
  }
)
Card.displayName = 'Card'

export const CardHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col space-y-1.5 mb-4', className)} {...props} />
)

export const CardTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn('text-lg font-semibold text-slate-100 tracking-tight', className)} {...props} />
)

export const CardDescription = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn('text-xs text-slate-400', className)} {...props} />
)

export const CardContent = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('', className)} {...props} />
)

export const CardFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex items-center pt-4 border-t border-slate-800/60 mt-4', className)} {...props} />
)
