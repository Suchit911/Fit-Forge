import React, { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  className?: string
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, description, children, className }) => {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousActiveElementRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }

      // Trap focus inside modal on Tab key
      if (e.key === 'Tab' && dialogRef.current) {
        const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
        if (focusableElements.length > 0) {
          const first = focusableElements[0]
          const last = focusableElements[focusableElements.length - 1]
          if (e.shiftKey) {
            if (document.activeElement === first) {
              e.preventDefault()
              last.focus()
            }
          } else {
            if (document.activeElement === last) {
              e.preventDefault()
              first.focus()
            }
          }
        }
      }
    }

    if (isOpen) {
      // Capture element that had focus prior to modal opening
      previousActiveElementRef.current = document.activeElement as HTMLElement | null

      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', handleKeyDown)
      // Focus first focusable element inside modal
      const timer = setTimeout(() => {
        if (dialogRef.current) {
          const firstFocusable = dialogRef.current.querySelector<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
          firstFocusable?.focus()
        }
      }, 50)
      return () => {
        clearTimeout(timer)
        document.body.style.overflow = 'auto'
        window.removeEventListener('keydown', handleKeyDown)
        // Restore focus to the element that triggered the modal
        if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
          previousActiveElementRef.current.focus()
        }
      }
    }

    return () => {
      document.body.style.overflow = 'auto'
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity cursor-pointer"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        aria-describedby={description ? 'modal-description' : undefined}
        className={cn(
          'relative z-50 w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:p-6 shadow-2xl transition-all max-h-[90vh] overflow-y-auto focus-visible:outline-none',
          className
        )}
      >
        <div className="flex items-start justify-between border-b border-slate-800 pb-4 mb-4 gap-3">
          <div className="min-w-0 flex-1">
            {title && (
              <h2 id="modal-title" className="text-lg font-bold text-slate-100 break-words">
                {title}
              </h2>
            )}
            {description && (
              <p id="modal-description" className="text-xs text-slate-400 mt-1 break-words">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}
