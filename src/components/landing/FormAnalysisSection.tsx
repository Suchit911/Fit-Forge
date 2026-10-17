import React from 'react'
import { Camera, CheckCircle2, ShieldAlert, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export const FormAnalysisSection: React.FC = () => {
  const checklist = [
    'Real-time form feedback',
    'Rep counting & tracking',
    'Posture & movement analysis',
    'Injury prevention',
  ]

  return (
    <section className="py-20 relative overflow-hidden">
      <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Text Column */}
          <div className="lg:col-span-5 space-y-6 text-left">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-1 text-xs font-bold text-cyan-400">
              <Camera className="h-3.5 w-3.5" />
              AI FORM ANALYSIS
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-100 leading-[1.15]">
              Perfect Your Form <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-300 to-emerald-400">
                With AI
              </span>
            </h2>

            <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
              Use your phone camera to get real-time feedback on your exercise form and prevent injuries. Our pose estimation technology analyzes depth, alignment, and tempo instantly.
            </p>

            <ul className="space-y-3 pt-2 text-xs font-semibold text-slate-200">
              {checklist.map((item, i) => (
                <li key={i} className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <div className="pt-4">
              <Link
                to="/form-analysis"
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-5 py-3 text-xs font-bold shadow-lg shadow-cyan-500/20 transition-all"
              >
                Try Form Analysis Mockup <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {/* Right Phone/Viewport Mockup Column */}
          <div className="lg:col-span-7 flex justify-center">
            <div className="relative w-full max-w-xl rounded-3xl border-4 border-slate-800 bg-slate-950 p-2 shadow-2xl">
              
              {/* Camera Viewport Frame */}
              <div className="relative aspect-[16/9] w-full rounded-2xl overflow-hidden bg-slate-900 border border-slate-800">
                <img
                  src="/assets/form_squat.jpg"
                  alt="Squat Form Pose Analysis"
                  className="w-full h-full object-cover opacity-80"
                />

                {/* Simulated Green Wireframe Skeleton Overlay */}
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <svg className="w-full h-full text-emerald-400 opacity-90" viewBox="0 0 100 100" fill="none">
                    {/* Head landmark */}
                    <circle cx="50" cy="38" r="3" stroke="#10b981" strokeWidth="1.5" fill="#10b98122" />
                    {/* Spine */}
                    <line x1="50" y1="41" x2="50" y2="68" stroke="#10b981" strokeWidth="1.5" />
                    {/* Shoulders */}
                    <line x1="42" y1="45" x2="58" y2="45" stroke="#10b981" strokeWidth="1.5" />
                    {/* Left arm */}
                    <line x1="42" y1="45" x2="38" y2="52" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="38" y1="52" x2="48" y2="50" stroke="#10b981" strokeWidth="1.5" />
                    {/* Right arm */}
                    <line x1="58" y1="45" x2="62" y2="52" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="62" y1="52" x2="52" y2="50" stroke="#10b981" strokeWidth="1.5" />
                    {/* Hips */}
                    <line x1="44" y1="68" x2="56" y2="68" stroke="#10b981" strokeWidth="1.5" />
                    {/* Legs */}
                    <line x1="44" y1="68" x2="40" y2="82" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="40" y1="82" x2="44" y2="92" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="56" y1="68" x2="60" y2="82" stroke="#10b981" strokeWidth="1.5" />
                    <line x1="60" y1="82" x2="56" y2="92" stroke="#10b981" strokeWidth="1.5" />
                    {/* Joint nodes */}
                    <circle cx="44" cy="68" r="1.5" fill="#06b6d4" />
                    <circle cx="56" cy="68" r="1.5" fill="#06b6d4" />
                    <circle cx="40" cy="82" r="1.5" fill="#06b6d4" />
                    <circle cx="60" cy="82" r="1.5" fill="#06b6d4" />
                  </svg>
                </div>

                {/* Top Left Status Badge */}
                <div className="absolute top-3 left-3 flex items-center gap-2 rounded-lg bg-slate-950/80 px-3 py-1.5 backdrop-blur-md border border-slate-800 text-[11px] font-mono font-bold text-slate-200">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  Squat • Rep 8 / 12
                </div>
              </div>

              {/* Floating Feedback Card overlay */}
              <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900 p-4 text-left space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase">Form Score</span>
                    <h4 className="text-base font-extrabold text-emerald-400">92% <span className="text-xs font-normal text-slate-200">Great Form!</span></h4>
                  </div>
                  <ShieldAlert className="h-5 w-5 text-emerald-400" />
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-medium text-slate-300">
                  <div className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Depth</div>
                  <div className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Knee Alignment</div>
                  <div className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Back Straight</div>
                  <div className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Range of Motion</div>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  )
}
