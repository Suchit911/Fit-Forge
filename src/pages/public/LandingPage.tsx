import React from 'react'
import { LandingNavbar } from '../../components/landing/LandingNavbar'
import { HeroSection } from '../../components/landing/HeroSection'
import { FeatureStrip } from '../../components/landing/FeatureStrip'
import { AICoachSection } from '../../components/landing/AICoachSection'
import { WorkoutSection } from '../../components/landing/WorkoutSection'
import { FormAnalysisSection } from '../../components/landing/FormAnalysisSection'
import { NutritionSection } from '../../components/landing/NutritionSection'
import { ProgressSection } from '../../components/landing/ProgressSection'
import { HowItWorksSection } from '../../components/landing/HowItWorksSection'
import { FeatureGrid } from '../../components/landing/FeatureGrid'
import { TransformationSection } from '../../components/landing/TransformationSection'
import { FinalCTASection } from '../../components/landing/FinalCTASection'
import { LandingFooter } from '../../components/landing/LandingFooter'

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#070a11] text-slate-100 selection:bg-emerald-500 selection:text-slate-950">
      <LandingNavbar />
      <main>
        <HeroSection />
        <FeatureStrip />
        <AICoachSection />
        <WorkoutSection />
        <FormAnalysisSection />
        <NutritionSection />
        <ProgressSection />
        <HowItWorksSection />
        <FeatureGrid />
        <TransformationSection />
        <FinalCTASection />
      </main>
      <LandingFooter />
    </div>
  )
}
