import React from 'react'
import { cn } from '../../lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:opacity-50 disabled:pointer-events-none cursor-pointer'

    const variants = {
      primary: 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 active:bg-emerald-600 font-semibold',
      secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 active:bg-slate-900 border border-slate-700',
      outline: 'border border-slate-700 text-slate-200 hover:bg-slate-800/60 active:bg-slate-800',
      ghost: 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100',
      danger: 'bg-red-600 text-white hover:bg-red-500 active:bg-red-700',
    }

    const sizes = {
      sm: 'min-h-[36px] px-3 text-xs',
      md: 'min-h-[44px] px-4 text-sm',
      lg: 'min-h-[48px] px-6 text-base font-semibold',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4 text-current" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading...
          </span>
        ) : (
          children
        )}
      </button>
    )
  }
)
Button.displayName = 'Button'
