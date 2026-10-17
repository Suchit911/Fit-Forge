import React, { useState } from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Navbar } from './Navbar'
import { MobileDrawer } from './MobileDrawer'
import { useUser } from '../../hooks/useUser'

export const AppShell: React.FC = () => {
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)
  const { user, authUser, isLoading, isAuthenticated } = useUser()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <span className="text-xs uppercase tracking-wider font-mono">Authenticating session...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated && !authUser) {
    return <Navigate to="/login" replace />
  }

  // Enforce onboarding: incomplete profiles cannot access dashboard or app shell
  if (user && user.profile_complete === false) {
    return <Navigate to="/onboarding" replace />
  }

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 antialiased">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Mobile Drawer */}
      <MobileDrawer isOpen={mobileDrawerOpen} onClose={() => setMobileDrawerOpen(false)} />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-x-hidden min-w-0">
        <Navbar onOpenMobileDrawer={() => setMobileDrawerOpen(true)} />
        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

