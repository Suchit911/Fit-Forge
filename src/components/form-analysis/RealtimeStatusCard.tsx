import React from 'react'

export interface RealtimeStatusCardProps {
  isAnalyzing?: boolean
  fps?: number
  connectionStatus?: string
}

export const RealtimeStatusCard: React.FC<RealtimeStatusCardProps> = ({
  isAnalyzing = false,
  fps = 0,
  connectionStatus = 'DISCONNECTED',
}) => {
  const isLive = isAnalyzing && connectionStatus === 'CONNECTED'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex items-center justify-between gap-4 text-left">
      <div className="space-y-1">
        <span className="text-[11px] font-bold text-slate-400 block uppercase">Real-time Stream</span>
        <span
          className={`flex items-center gap-1.5 text-xs font-mono font-bold ${
            isLive ? 'text-emerald-400' : 'text-slate-400'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isLive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
            }`}
          />
          {isLive ? `Live (${fps} FPS)` : connectionStatus === 'CONNECTING' ? 'Connecting...' : 'Standby'}
        </span>
      </div>

      <div className="text-right font-mono text-[11px] text-slate-500">
        {isLive ? (
          <span className="text-emerald-400 font-bold">25 FPS Target</span>
        ) : (
          <span>Stream Inactive</span>
        )}
      </div>
    </div>
  )
}
