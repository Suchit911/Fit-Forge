import React from 'react'
import type { ConnectedDeviceItem } from '../../types'
import { Smartphone, Watch, Activity, Heart, Scale, Check, ChevronRight } from 'lucide-react'

export interface ConnectedDevicesCardProps {
  devices: ConnectedDeviceItem[]
  onToggleConnection: (id: string) => void
  onManageClick: () => void
}

export const ConnectedDevicesCard: React.FC<ConnectedDevicesCardProps> = ({
  devices,
  onToggleConnection,
  onManageClick,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'watch':
        return <Watch className="h-4 w-4 text-blue-400" />
      case 'activity':
        return <Activity className="h-4 w-4 text-blue-400" />
      case 'heart':
        return <Heart className="h-4 w-4 text-blue-400" />
      case 'scale':
        return <Scale className="h-4 w-4 text-blue-400" />
      default:
        return <Smartphone className="h-4 w-4 text-blue-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Smartphone className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-100">Connected Devices</h3>
        </div>

        <div className="space-y-2.5 font-mono text-xs">
          {devices.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 shrink-0">
                  {getIcon(d.iconName)}
                </div>
                <div className="space-y-0.5 font-sans">
                  <h4 className="text-xs font-bold text-slate-100">{d.name}</h4>
                  <p className="text-[10px] text-slate-400">{d.description}</p>
                </div>
              </div>

              {d.isConnected ? (
                <span className="text-xs font-extrabold text-emerald-400 flex items-center gap-1">
                  Connected <Check className="h-4 w-4 rounded-full bg-emerald-500/20 p-0.5" />
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => onToggleConnection(d.id)}
                  className="rounded-xl border border-blue-500/40 bg-blue-500/10 hover:bg-blue-500 hover:text-slate-950 px-3 py-1 text-xs font-bold text-blue-400 transition-all cursor-pointer"
                >
                  Connect
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="pt-2 border-t border-slate-800/80">
        <button
          type="button"
          onClick={onManageClick}
          className="flex items-center justify-between w-full text-xs font-mono text-blue-400 hover:text-blue-300 font-bold transition-colors"
        >
          <span>Manage All Devices</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
