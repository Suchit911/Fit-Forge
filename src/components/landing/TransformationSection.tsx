import React from 'react'
import { Star, Quote, Award } from 'lucide-react'

export const TransformationSection: React.FC = () => {
  const stats = [
    { value: '50K+', label: 'Happy Users' },
    { value: '1M+', label: 'Workouts Completed' },
    { value: '4.9★', label: 'App Store Rating' },
    { value: '92%', label: 'Goal Achievement' },
  ]

  return (
    <section className="py-20 bg-slate-950/60 border-y border-slate-800/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        
        {/* Header */}
        <div className="text-left mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-bold text-emerald-400 mb-3">
            <Award className="h-3.5 w-3.5" />
            REAL PEOPLE. REAL TRANSFORMATIONS.
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight">
            Transformations That Inspire
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Transformation Highlight Card */}
          <div className="lg:col-span-7 flex flex-col sm:flex-row gap-6 items-center rounded-3xl border border-slate-800 bg-slate-900 p-6 text-left">
            {/* Before & After Image Placeholder Container */}
            <div className="relative w-full sm:w-64 aspect-[4/3] sm:aspect-[3/4] rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
              <img
                src="/assets/form_squat.jpg"
                alt="Fitness Transformation"
                className="w-full h-full object-cover opacity-80"
              />
              <div className="absolute top-2 left-2 rounded-md bg-slate-950/80 px-2 py-0.5 text-[10px] font-mono text-slate-300 border border-slate-800">
                Before
              </div>
              <div className="absolute bottom-2 right-2 rounded-md bg-emerald-500 px-2 py-0.5 text-[10px] font-mono font-bold text-slate-950">
                After
              </div>
            </div>

            {/* Testimonial Quote */}
            <div className="space-y-3">
              <Quote className="h-6 w-6 text-emerald-400 opacity-60" />
              <p className="text-xs sm:text-sm text-slate-200 leading-relaxed italic">
                "AI Fitness changed my life. The personalized workouts and nutrition plan helped me lose 18kg and build visible muscle confidence."
              </p>
              <div>
                <h4 className="text-xs font-bold text-slate-100">David K.</h4>
                <p className="text-[10px] text-emerald-400 font-mono">Lost 18kg in 6 months</p>
              </div>
              <div className="flex text-amber-400 gap-0.5 pt-1">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="h-3.5 w-3.5 fill-amber-400" />
                ))}
              </div>
            </div>
          </div>

          {/* Right Stat Grid */}
          <div className="lg:col-span-5 grid grid-cols-2 gap-4">
            {stats.map((s, i) => (
              <div
                key={i}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-center space-y-1"
              >
                <span className="text-3xl font-extrabold text-slate-100 font-mono block">{s.value}</span>
                <span className="text-xs text-slate-400">{s.label}</span>
              </div>
            ))}
          </div>

        </div>

      </div>
    </section>
  )
}
