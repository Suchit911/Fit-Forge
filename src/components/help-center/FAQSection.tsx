import React, { useState } from 'react'
import type { FaqItem } from '../../types'
import { ChevronDown, ChevronUp, Search, HelpCircle } from 'lucide-react'

export interface FAQSectionProps {
  faqs: FaqItem[]
  onViewAllClick: () => void
  onContactSupportClick: () => void
}

export const FAQSection: React.FC<FAQSectionProps> = ({
  faqs,
  onViewAllClick,
  onContactSupportClick,
}) => {
  const [openIds, setOpenIds] = useState<string[]>(['faq1'])

  const toggleFaq = (id: string) => {
    setOpenIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Frequently Asked Questions</h3>
        <button
          type="button"
          onClick={onViewAllClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 cursor-pointer"
        >
          View All FAQs
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left Accordion (7 of 12 cols) */}
        <div className="lg:col-span-7 space-y-2 font-mono text-xs">
          {faqs.map((faq) => {
            const isOpen = openIds.includes(faq.id)

            return (
              <div
                key={faq.id}
                className="rounded-2xl border border-slate-800 bg-slate-950/60 overflow-hidden transition-colors"
              >
                <button
                  type="button"
                  onClick={() => toggleFaq(faq.id)}
                  className="flex items-center justify-between w-full p-3.5 text-left font-bold text-slate-100 hover:text-emerald-400 transition-colors cursor-pointer"
                >
                  <span className="text-xs">{faq.question}</span>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-emerald-400 shrink-0 ml-2" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-slate-500 shrink-0 ml-2" />
                  )}
                </button>

                {isOpen && (
                  <div className="px-3.5 pb-3.5 pt-0 font-sans text-xs text-slate-400 border-t border-slate-800/50 leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Right Futuristic FAQ Graphic (5 of 12 cols) */}
        <div className="lg:col-span-5 flex items-center justify-center p-4">
          <div className="relative flex h-48 w-full max-w-[260px] flex-col items-center justify-center rounded-3xl border border-emerald-500/20 bg-slate-950/80 p-4 shadow-2xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 via-transparent to-cyan-500/10" />

            {/* Document Clipboard SVG Graphic */}
            <div className="relative z-10 flex flex-col items-center justify-center space-y-2">
              <div className="relative flex h-24 w-20 flex-col items-center justify-center rounded-2xl border-2 border-emerald-500/40 bg-slate-900 shadow-xl">
                <div className="absolute -top-2 h-3 w-8 rounded-full bg-emerald-500/30 border border-emerald-500/50" />
                <span className="text-base font-extrabold text-emerald-400 tracking-wider">FAQ</span>
                <div className="w-12 h-0.5 bg-emerald-500/30 my-1 rounded-full" />
                <div className="w-10 h-0.5 bg-slate-700 my-0.5 rounded-full" />
                <div className="w-8 h-0.5 bg-slate-700 my-0.5 rounded-full" />
              </div>

              {/* Floating Magnifying Glass & Question Mark */}
              <div className="absolute -right-2 top-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 border border-emerald-500/40 text-emerald-400 shadow-lg">
                <Search className="h-5 w-5" />
              </div>
              <div className="absolute -left-2 bottom-4 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 border border-cyan-500/40 text-cyan-400 shadow-lg">
                <HelpCircle className="h-4 w-4" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Link */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
        <span className="text-slate-400 font-sans">Can't find what you're looking for?</span>
        <button
          type="button"
          onClick={onContactSupportClick}
          className="font-bold text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
        >
          Contact Support &gt;
        </button>
      </div>
    </div>
  )
}
