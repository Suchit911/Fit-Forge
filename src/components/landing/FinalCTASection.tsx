import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Trophy, CheckCircle2 } from 'lucide-react'

export const FinalCTASection: React.FC = () => {
  return (
    <section className="py-20 relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        <div className="relative rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-8 sm:p-12 text-center overflow-hidden green-glow">
          
          {/* Background Ambient Accents */}
          <div className="absolute -top-24 -left-24 w-64 h-64 bg-emerald-500/10 rounded-full blur-[80px] pointer-events-none" />
          <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px] pointer-events-none" />

          {/* Trophy Icon Badge */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <Trophy className="h-8 w-8" />
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 max-w-2xl mx-auto leading-tight">
            Ready to Transform Your <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
              Fitness Journey?
            </span>
          </h2>

          <p className="text-xs sm:text-sm text-slate-400 mt-4 max-w-lg mx-auto">
            Join thousands of people who are achieving their fitness goals with personalized AI guidance.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-8 py-4 text-sm font-extrabold shadow-lg shadow-emerald-500/30 transition-all hover:scale-105"
            >
              Start Your Free Journey <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 flex items-center justify-center gap-2 text-xs font-semibold text-slate-400">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>No credit card required</span>
          </div>

        </div>

      </div>
    </section>
  )
}
