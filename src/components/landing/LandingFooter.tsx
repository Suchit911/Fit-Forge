import React from 'react'
import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'

export const LandingFooter: React.FC = () => {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950 pt-16 pb-12 text-left text-xs text-slate-400">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 pb-12 border-b border-slate-900">
          
          {/* Column 1: Brand Info */}
          <div className="lg:col-span-2 space-y-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-slate-950 font-bold">
                <Flame className="h-5 w-5" />
              </div>
              <span className="text-base font-extrabold text-slate-100">
                AI <span className="text-emerald-400">FITNESS</span>
              </span>
            </Link>
            <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
              Your AI-powered fitness coach for a stronger, healthier you. Personalized workouts, nutrition, and computer vision form feedback.
            </p>
            <div className="flex items-center gap-3 pt-2 text-slate-400">
              <a href="#" className="hover:text-emerald-400 transition-colors" aria-label="Instagram">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
              </a>
              <a href="#" className="hover:text-emerald-400 transition-colors" aria-label="YouTube">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/></svg>
              </a>
              <a href="#" className="hover:text-emerald-400 transition-colors" aria-label="Twitter">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </a>
            </div>
          </div>

          {/* Column 2: Product Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">Product</h4>
            <ul className="space-y-2">
              <li><a href="#features" className="hover:text-slate-200">Features</a></li>
              <li><a href="#workouts" className="hover:text-slate-200">Workouts</a></li>
              <li><a href="#nutrition" className="hover:text-slate-200">Nutrition</a></li>
              <li><a href="#progress" className="hover:text-slate-200">Progress</a></li>
              <li><a href="#ai-coach" className="hover:text-slate-200">AI Coach</a></li>
            </ul>
          </div>

          {/* Column 3: Company Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">Company</h4>
            <ul className="space-y-2">
              <li><Link to="/about" className="hover:text-slate-200">About Us</Link></li>
              <li><a href="#" className="hover:text-slate-200">Blog</a></li>
              <li><a href="#" className="hover:text-slate-200">Careers</a></li>
              <li><a href="#" className="hover:text-slate-200">Contact</a></li>
            </ul>
          </div>

          {/* Column 4: Support & App Store */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">Support</h4>
            <ul className="space-y-2">
              <li><a href="#" className="hover:text-slate-200">Help Center</a></li>
              <li><a href="#" className="hover:text-slate-200">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-slate-200">Terms of Service</a></li>
              <li><a href="#" className="hover:text-slate-200">Refund Policy</a></li>
            </ul>
            <div className="pt-2 space-y-2">
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-200">Download App</h4>
              <div className="flex flex-col gap-2">
                <button className="flex items-center justify-center gap-2 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-[11px] font-semibold text-slate-200 hover:bg-slate-800">
                  <span>App Store</span>
                </button>
                <button className="flex items-center justify-center gap-2 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-[11px] font-semibold text-slate-200 hover:bg-slate-800">
                  <span>Google Play</span>
                </button>
              </div>
            </div>
          </div>

        </div>

        {/* Bottom Copyright */}
        <div className="pt-8 text-center text-[11px] text-slate-500 font-mono">
          © 2026 AI Fitness Platform. All rights reserved.
        </div>

      </div>
    </footer>
  )
}
