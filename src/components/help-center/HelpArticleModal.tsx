import React from 'react'
import { Modal, Button } from '../ui'
import { BookOpen, Clock } from 'lucide-react'

export interface HelpArticleModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  description: string
  readTime?: string
}

export const HelpArticleModal: React.FC<HelpArticleModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  readTime = '4 min read',
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4 text-left font-mono text-xs pt-1">
        <div className="flex items-center gap-2 text-emerald-400 font-bold">
          <Clock className="h-4 w-4" />
          <span>{readTime}</span>
        </div>

        <p className="text-slate-300 font-sans leading-relaxed text-sm">{description}</p>

        <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2 font-sans">
          <h4 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
            <BookOpen className="h-4 w-4 text-emerald-400" /> Article Key Takeaways
          </h4>
          <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
            <li>Ensure proper camera framing for computer vision accuracy.</li>
            <li>Sync your wearable before starting high-intensity sessions.</li>
            <li>Consult AI Coach for adaptive rest intervals during sets.</li>
          </ul>
        </div>

        <div className="pt-2">
          <Button type="button" variant="primary" onClick={onClose} className="w-full">
            Done Reading
          </Button>
        </div>
      </div>
    </Modal>
  )
}
