import React from 'react'
import type { ProgressPhotoItem } from '../../types'

export interface ProgressPhotosCardProps {
  photos: ProgressPhotoItem[]
}

export const ProgressPhotosCard: React.FC<ProgressPhotosCardProps> = ({ photos }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Progress Photos</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {photos.map((photo) => (
          <div
            key={photo.id}
            className="group relative rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden transition-all hover:border-emerald-500/50 cursor-pointer"
          >
            <div className="relative aspect-[3/4] w-full overflow-hidden">
              <img
                src={photo.imageUrl}
                alt={photo.date}
                className="w-full h-full object-cover opacity-85 group-hover:scale-105 transition-transform duration-300"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent" />
            </div>

            <div className="p-2 text-center bg-slate-900/90 border-t border-slate-800/80">
              <span className="text-[10px] font-mono font-bold text-slate-300 block">{photo.date}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
