import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui'

export const FeaturesPage: React.FC = () => (
  <div className="p-8 max-w-4xl mx-auto space-y-4 text-center">
    <h1 className="text-2xl font-bold text-slate-100">Platform Features</h1>
    <p className="text-xs text-slate-400">Adaptive Workouts, Computer Vision Form Feedback, Nutrition RAG</p>
    <Link to="/"><Button variant="outline" size="sm">Back to Home</Button></Link>
  </div>
)
export const PricingPage: React.FC = () => (
  <div className="p-8 max-w-4xl mx-auto space-y-4 text-center">
    <h1 className="text-2xl font-bold text-slate-100">Pricing Plans</h1>
    <p className="text-xs text-slate-400">Free Tier & Premium Coaching Access</p>
    <Link to="/"><Button variant="outline" size="sm">Back to Home</Button></Link>
  </div>
)
export const AboutPage: React.FC = () => (
  <div className="p-8 max-w-4xl mx-auto space-y-4 text-center">
    <h1 className="text-2xl font-bold text-slate-100">About AI FITNESS</h1>
    <p className="text-xs text-slate-400">Evidence-based adaptive personal fitness intelligence</p>
    <Link to="/"><Button variant="outline" size="sm">Back to Home</Button></Link>
  </div>
)
