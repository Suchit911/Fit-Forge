import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'

// Layouts
import { AppShell } from './components/layout/AppShell'

// Public Pages
import { LandingPage } from './pages/public/LandingPage'
import { FeaturesPage, PricingPage, AboutPage } from './pages/public/FeaturesPage'

// Auth Pages
import { LoginPage, SignupPage, ForgotPasswordPage } from './pages/auth/LoginPage'
import { OnboardingPage } from './pages/onboarding/OnboardingPage'

// App Pages
import { DashboardPage } from './pages/app/DashboardPage'
import { WorkoutsPage } from './pages/app/WorkoutsPage'
import { WorkoutDetailsPage } from './pages/app/WorkoutDetailsPage'
import { ActiveWorkoutPage } from './pages/app/ActiveWorkoutPage'
import { ExercisesPage } from './pages/app/ExercisesPage'
import { ExerciseDetailsPage } from './pages/app/ExerciseDetailsPage'
import { FormAnalysisPage } from './pages/app/FormAnalysisPage'
import { NutritionPage } from './pages/app/NutritionPage'
import { ProgressPage } from './pages/app/ProgressPage'
import { AICoachPage } from './pages/app/AICoachPage'
import { AchievementsPage } from './pages/app/AchievementsPage'
import { ProfilePage } from './pages/app/ProfilePage'
import { SettingsPage } from './pages/app/SettingsPage'
import { HelpCenterPage } from './pages/app/HelpCenterPage'
import { NotificationsPage } from './pages/app/NotificationsPage'

import { ToastProvider } from './components/ui/Toast'
import { NotFoundPage } from './pages/app/NotFoundPage'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/landing" element={<Navigate to="/" replace />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/about" element={<AboutPage />} />

            {/* Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />

            {/* Onboarding Wizard */}
            <Route path="/onboarding" element={<OnboardingPage />} />

            {/* Protected Application Routes */}
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/workouts" element={<WorkoutsPage />} />
              <Route path="/workouts/today" element={<WorkoutDetailsPage />} />
              <Route path="/workouts/history" element={<WorkoutsPage />} />
              <Route path="/workouts/:id" element={<WorkoutDetailsPage />} />
              <Route path="/workouts/:id/active" element={<ActiveWorkoutPage />} />
              <Route path="/exercises" element={<ExercisesPage />} />
              <Route path="/exercises/:id" element={<ExerciseDetailsPage />} />
              <Route path="/form-analysis" element={<FormAnalysisPage />} />
              <Route path="/nutrition" element={<NutritionPage />} />
              <Route path="/progress" element={<ProgressPage />} />
              <Route path="/coach" element={<AICoachPage />} />
              <Route path="/achievements" element={<AchievementsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/help-center" element={<HelpCenterPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              
              {/* 404 Fallback within AppShell */}
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}


export default App
