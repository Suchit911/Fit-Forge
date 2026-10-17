import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Flame, Menu, X } from 'lucide-react'

export const LandingNavbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const navLinks = [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Workouts', href: '#workouts' },
    { label: 'Nutrition', href: '#nutrition' },
    { label: 'Progress', href: '#progress' },
    { label: 'Pricing', href: '#pricing' },
  ]

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-slate-950 font-bold shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
            <Flame className="h-5 w-5" />
          </div>
          <span className="text-base font-extrabold tracking-tight text-slate-100">
            AI <span className="text-emerald-400">FITNESS</span>
          </span>
        </Link>

        {/* Center Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-6">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-xs font-medium text-slate-300 hover:text-emerald-400 transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/login"
            className="text-xs font-semibold text-slate-300 hover:text-slate-100 px-3 py-2 transition-colors"
          >
            Log In
          </Link>
          <Link
            to="/signup"
            className="inline-flex items-center justify-center rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-4 py-2 text-xs font-bold shadow-md shadow-emerald-500/20 transition-all hover:scale-[1.02]"
          >
            Get Started
          </Link>
        </div>

        {/* Mobile Menu Trigger */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-100"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-slate-950 px-4 pt-2 pb-6 space-y-3">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-300 hover:text-emerald-400"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-4 border-t border-slate-900 flex flex-col gap-2">
            <Link
              to="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-2 text-sm font-medium text-slate-300 bg-slate-900 rounded-lg"
            >
              Log In
            </Link>
            <Link
              to="/signup"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-2 text-sm font-bold text-slate-950 bg-emerald-500 rounded-lg"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}
