import React, { useState } from 'react'
import type { AIChatMessage } from '../../types'
import { Bot, Share2, MoreVertical, Send, ThumbsUp, ThumbsDown, Copy, Trash2 } from 'lucide-react'
import { useToast } from '../ui/Toast'

export interface ChatConversationViewProps {
  title: string
  messages: AIChatMessage[]
  suggestedPrompts: string[]
  onSendMessage: (text: string) => void
  onPromptClick: (prompt: string) => void
  onShareChat: () => void
  isSending?: boolean
  onDeleteChat?: () => void
}

export const ChatConversationView: React.FC<ChatConversationViewProps> = ({
  title,
  messages,
  suggestedPrompts,
  onSendMessage,
  onPromptClick,
  onShareChat,
  isSending = false,
  onDeleteChat,
}) => {
  const [inputText, setInputText] = useState('')
  const [showOptions, setShowOptions] = useState(false)
  const { showToast } = useToast()

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim() || isSending) return
    onSendMessage(inputText)
    setInputText('')
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Message copied to clipboard', 'info')
    }).catch(() => {
      showToast('Could not copy message', 'error')
    })
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl flex flex-col justify-between h-full min-h-[520px]">
      
      {/* Active Conversation Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
              {title}
            </h3>
            <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> AI Coach
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 relative">
          <button
            type="button"
            onClick={onShareChat}
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs font-mono text-slate-300 hover:border-slate-700 transition-colors"
          >
            <Share2 className="h-3.5 w-3.5" /> Share Chat
          </button>
          {onDeleteChat && (
            <div className="relative">
              <button
                type="button"
                aria-label="More options"
                onClick={() => setShowOptions(!showOptions)}
                className="p-1 text-slate-400 hover:text-slate-200"
              >
                <MoreVertical className="h-4 w-4" />
              </button>
              {showOptions && (
                <div className="absolute right-0 top-8 z-20 w-36 rounded-xl border border-slate-800 bg-slate-950 p-1 shadow-2xl font-mono text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setShowOptions(false)
                      onDeleteChat()
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-rose-400 hover:bg-rose-950/40 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete Chat
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="space-y-4 flex-1 overflow-y-auto pr-1">
        {messages.length === 0 && !isSending ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3 my-auto">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Bot className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-slate-200">Start a new conversation</h4>
              <p className="text-xs text-slate-400 max-w-xs">
                Ask your AI Coach about training splits, progressive overload, recovery, or nutrition.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user'

            return (
              <div
                key={msg.id}
                className={`flex gap-3 text-xs leading-relaxed ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0 mt-1">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-xl rounded-2xl p-4 space-y-2 border ${
                    isUser
                      ? 'bg-emerald-950/60 border-emerald-500/40 text-slate-100'
                      : 'bg-slate-950/80 border-slate-800 text-slate-200'
                  }`}
                >
                  <div className="whitespace-pre-line text-xs">{msg.text}</div>

                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/40">
                    <span>{msg.timestamp}</span>

                    {!isUser && (
                      <div className="flex items-center gap-2">
                        <button type="button" aria-label="Thumbs up" className="hover:text-emerald-400 transition-colors">
                          <ThumbsUp className="h-3 w-3" />
                        </button>
                        <button type="button" aria-label="Thumbs down" className="hover:text-rose-400 transition-colors">
                          <ThumbsDown className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          aria-label="Copy"
                          onClick={() => handleCopy(msg.text)}
                          className="hover:text-cyan-400 transition-colors"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}

        {/* Typing indicator bubble while waiting for real assistant response */}
        {isSending && (
          <div className="flex gap-3 text-xs leading-relaxed justify-start">
            <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0 mt-1">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl px-4 py-3 border bg-slate-950/80 border-slate-800 text-slate-400 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-bounce" />
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}
      </div>

      {/* Suggested Prompt Chips */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60 text-xs font-mono">
        {suggestedPrompts.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onPromptClick(prompt)}
            disabled={isSending}
            className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-slate-300 hover:border-emerald-500/50 hover:text-emerald-400 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Input & Disclaimer */}
      <div className="space-y-2">
        <form onSubmit={handleSend} className="relative w-full">
          <input
            type="text"
            value={inputText}
            disabled={isSending}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={isSending ? "AI Coach is generating advice..." : "Ask your AI coach anything..."}
            className="w-full h-12 rounded-2xl border border-slate-800 bg-slate-950 pl-4 pr-14 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={isSending || !inputText.trim()}
            aria-label="Send message"
            className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>

        <span className="text-[10px] text-slate-500 font-mono block text-center">
          AI Coach can make mistakes. Please verify important information.
        </span>
      </div>

    </div>
  )
}
