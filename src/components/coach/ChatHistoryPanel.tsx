import React from 'react'
import type { AIChatConversation } from '../../types'
import { Plus, MessageSquare, MoreVertical, ChevronRight } from 'lucide-react'

export interface ChatHistoryPanelProps {
  conversations: AIChatConversation[]
  activeId: string
  onSelectConversation: (id: string) => void
  onNewChatClick: () => void
  onDeleteConversation?: (id: string) => void
}

export const ChatHistoryPanel: React.FC<ChatHistoryPanelProps> = ({
  conversations,
  activeId,
  onSelectConversation,
  onNewChatClick,
  onDeleteConversation,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-4 space-y-3 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100">Chats</h3>
          <button
            type="button"
            onClick={onNewChatClick}
            aria-label="Create new chat"
            className="flex h-6 w-6 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Conversation List */}
        <div className="space-y-2 font-mono text-xs overflow-y-auto max-h-[480px] pr-0.5">
          {conversations.length === 0 ? (
            <div className="text-center py-6 text-slate-500 font-sans text-xs space-y-1">
              <p className="font-semibold text-slate-400">No chats yet</p>
              <p className="text-[10px]">Click + above or send a message to start.</p>
            </div>
          ) : (
            conversations.map((c) => {
              const isActive = c.id === activeId

              return (
                <div
                  key={c.id}
                  onClick={() => onSelectConversation(c.id)}
                  className={`p-2.5 rounded-2xl border transition-all cursor-pointer space-y-1 ${
                    isActive
                      ? 'border-emerald-500/50 bg-emerald-950/30 shadow-md shadow-emerald-950/40'
                      : 'border-slate-800/80 bg-slate-950/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1">
                      <MessageSquare className="h-3 w-3 text-emerald-400" /> {c.dateGroup}
                    </span>
                    <span className="text-[10px] text-slate-500">{c.timestamp}</span>
                  </div>

                  <div className="flex items-start justify-between gap-1">
                    <h4
                      className={`text-xs font-bold truncate ${
                        isActive ? 'text-emerald-400' : 'text-slate-200'
                      }`}
                    >
                      {c.title}
                    </h4>
                    {onDeleteConversation && (
                      <button
                        type="button"
                        aria-label={`Delete conversation ${c.title}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          if (window.confirm(`Delete conversation "${c.title}"?`)) {
                            onDeleteConversation(c.id)
                          }
                        }}
                        className="text-slate-500 hover:text-rose-400 transition-colors p-0.5"
                      >
                        <MoreVertical className="h-3.5 w-3.5 shrink-0" />
                      </button>
                    )}
                  </div>

                  <p className="text-[10px] font-sans text-slate-400 line-clamp-1 leading-tight">
                    {c.previewText}
                  </p>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* View All Chats Link */}
      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          className="w-full flex items-center justify-between text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span>{conversations.length} Active {conversations.length === 1 ? 'Chat' : 'Chats'}</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
