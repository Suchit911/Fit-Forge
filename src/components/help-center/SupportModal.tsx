import React, { useState } from 'react'
import { Modal, Button, Input } from '../ui'
import { Check, Send } from 'lucide-react'

export interface SupportModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  subtitle?: string
}

export const SupportModal: React.FC<SupportModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle = 'Get in touch with our AI FITNESS support team.',
}) => {
  const [message, setMessage] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    setTimeout(() => {
      setSubmitted(false)
      setMessage('')
      onClose()
    }, 600)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4 text-left font-mono text-xs pt-1">
        {submitted ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              <Check className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-extrabold text-slate-100">Ticket Submitted</h4>
            <p className="text-xs text-slate-400 font-sans">Our support team will respond within 24 hours.</p>
          </div>
        ) : (
          <>
            <p className="text-slate-300 font-sans text-xs">{subtitle}</p>

            {title.includes('System Status') ? (
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="font-bold text-slate-200">API Server Response Time</span>
                  <span className="text-emerald-400 font-extrabold">24 ms (Normal)</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="font-bold text-slate-200">Pose Estimation Uptime</span>
                  <span className="text-emerald-400 font-extrabold">99.98%</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="font-bold text-slate-200">Database Sync Latency</span>
                  <span className="text-emerald-400 font-extrabold">12 ms</span>
                </div>
              </div>
            ) : (
              <>
                <Input
                  label="Subject / Topic"
                  placeholder="e.g. Issue with workout log or wearable sync"
                  required
                />

                <div className="space-y-1">
                  <label className="text-slate-300 font-bold block">Description</label>
                  <textarea
                    rows={4}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Describe what happened or ask a question..."
                    required
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </>
            )}

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
                Close
              </Button>
              {!title.includes('System Status') && (
                <Button type="submit" variant="primary" className="flex-1 inline-flex items-center justify-center gap-1.5">
                  <Send className="h-3.5 w-3.5" /> Submit Request
                </Button>
              )}
            </div>
          </>
        )}
      </form>
    </Modal>
  )
}
