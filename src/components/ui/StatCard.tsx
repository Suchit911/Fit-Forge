import React from 'react'
import { Card } from './Card'
import { cn } from '../../lib/utils'

export interface StatCardProps {
  label: string
  value: string | number
  subtext?: string
  icon?: React.ReactNode
  trend?: {
    value: string
    isPositive: boolean
  }
  className?: string
}

export const StatCard: React.FC<StatCardProps> = ({ label, value, subtext, icon, trend, className }) => {
  return (
    <Card className={cn('flex flex-col justify-between p-4', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-slate-100">{value}</span>
        {trend && (
          <span className={cn('text-xs font-medium', trend.isPositive ? 'text-emerald-400' : 'text-red-400')}>
            {trend.isPositive ? '+' : ''}
            {trend.value}
          </span>
        )}
      </div>
      {subtext && <p className="mt-1 text-xs text-slate-500">{subtext}</p>}
    </Card>
  )
}
