import React, { createContext, useContext, useState } from 'react'
import { cn } from '../../lib/utils'

interface TabsContextType {
  activeTab: string
  setActiveTab: (value: string) => void
}

const TabsContext = createContext<TabsContextType | undefined>(undefined)

export interface TabsProps {
  defaultValue: string
  value?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  className?: string
}

export const Tabs: React.FC<TabsProps> = ({ defaultValue, value, onValueChange, children, className }) => {
  const [selected, setSelected] = useState(defaultValue)
  const activeTab = value !== undefined ? value : selected

  const handleTabChange = (val: string) => {
    setSelected(val)
    if (onValueChange) onValueChange(val)
  }

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab: handleTabChange }}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  )
}

export const TabsList: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => {
  return (
    <div className={cn('inline-flex items-center justify-center rounded-lg bg-slate-900 p-1 text-slate-400 border border-slate-800', className)}>
      {children}
    </div>
  )
}

export const TabsTrigger: React.FC<{ value: string; children: React.ReactNode; className?: string }> = ({
  value,
  children,
  className,
}) => {
  const context = useContext(TabsContext)
  if (!context) throw new Error('TabsTrigger must be used within Tabs')

  const isActive = context.activeTab === value

  return (
    <button
      type="button"
      onClick={() => context.setActiveTab(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer',
        isActive ? 'bg-slate-800 text-slate-100 shadow-sm font-semibold' : 'hover:text-slate-200',
        className
      )}
    >
      {children}
    </button>
  )
}

export const TabsContent: React.FC<{ value: string; children: React.ReactNode; className?: string }> = ({
  value,
  children,
  className,
}) => {
  const context = useContext(TabsContext)
  if (!context) throw new Error('TabsContent must be used within Tabs')

  if (context.activeTab !== value) return null

  return <div className={cn('mt-4 outline-none', className)}>{children}</div>
}
