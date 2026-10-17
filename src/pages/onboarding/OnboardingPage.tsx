import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Input, Button, useToast } from '../../components/ui'
import { useUser } from '../../hooks/useUser'
import type { DifficultyLevel, FitnessGoal, Environment, EquipmentType, UserProfile } from '../../types'
import {
  User,
  Target,
  Dumbbell,
  Utensils,
  ArrowRight,
  ArrowLeft,
  Check,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  Activity,
  Flame,
  Zap,
  Heart,
  Calculator,
} from 'lucide-react'

const GOAL_OPTIONS: { id: FitnessGoal; title: string; desc: string; icon: typeof Target }[] = [
  { id: 'muscle_gain', title: 'Muscle Hypertrophy', desc: 'Build lean muscle mass and enhance physique', icon: Dumbbell },
  { id: 'fat_loss', title: 'Fat Loss & Shred', desc: 'Reduce body fat while maintaining muscle definition', icon: Flame },
  { id: 'strength', title: 'Pure Strength', desc: 'Increase raw power, 1RM, and compound lift numbers', icon: Zap },
  { id: 'endurance', title: 'Endurance & Cardio', desc: 'Build aerobic capacity, stamina, and work capacity', icon: Activity },
  { id: 'general_fitness', title: 'General Fitness', desc: 'Improve mobility, cardiovascular health, and daily energy', icon: Heart },
]

const FITNESS_LEVELS: { id: DifficultyLevel; title: string; subtitle: string }[] = [
  { id: 'beginner', title: 'Beginner', subtitle: 'New to training or returning after a long break (< 1 yr)' },
  { id: 'intermediate', title: 'Intermediate', subtitle: 'Consistent structured training for 1–3 years' },
  { id: 'advanced', title: 'Advanced', subtitle: 'Disciplined progressive overload for 3+ years' },
]

const EQUIPMENT_OPTIONS: { id: EquipmentType; label: string }[] = [
  { id: 'bodyweight', label: 'Bodyweight' },
  { id: 'dumbbells', label: 'Dumbbells' },
  { id: 'barbell', label: 'Barbell & Plates' },
  { id: 'kettlebell', label: 'Kettlebells' },
  { id: 'resistance_bands', label: 'Resistance Bands' },
  { id: 'cable_machine', label: 'Cable Machine' },
  { id: 'pull_up_bar', label: 'Pull-up Bar' },
  { id: 'yoga_mat', label: 'Yoga Mat' },
]

export const OnboardingPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, authUser, isLoading: isUserLoading, updateProfile, isUpdating } = useUser()
  const { showToast } = useToast()

  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Form State
  const [formData, setFormData] = useState({
    // Step 1: Personal
    name: '',
    gender: '',
    age: '',
    heightCm: '',
    weightKg: '',
    // Step 2: Goals
    primaryGoal: 'muscle_gain' as FitnessGoal,
    fitnessLevel: 'intermediate' as DifficultyLevel,
    targetWeightKg: '',
    // Step 3: Preferences
    environment: 'gym' as Environment,
    workoutFrequencyDaysPerWeek: 4,
    workoutDurationMinutes: 60,
    preferredWorkoutType: 'Strength & Hypertrophy',
    preferredTrainingTime: 'Morning',
    availableEquipment: ['bodyweight', 'dumbbells', 'barbell'] as EquipmentType[],
    // Step 4: Nutrition
    dietaryPreference: 'Standard / Balanced',
    targetCalories: '',
    targetProteinGrams: '',
    targetCarbsGrams: '',
    targetFatGrams: '',
    hydrationGoalLiters: '',
  })

  // Initialize name from auth user or existing profile; redirect if already complete
  useEffect(() => {
    if (user?.profile_complete) {
      navigate('/dashboard', { replace: true })
      return
    }
    if (user?.name) {
      setFormData((prev) => ({ ...prev, name: user.name }))
    } else if (authUser?.displayName) {
      setFormData((prev) => ({ ...prev, name: authUser.displayName || '' }))
    }
  }, [user, authUser, navigate])

  // Helper to check if biometrics are available for auto-calculation
  const hasBiometrics = Boolean(
    formData.age && !isNaN(Number(formData.age)) && Number(formData.age) > 0 &&
    formData.heightCm && !isNaN(Number(formData.heightCm)) && Number(formData.heightCm) > 0 &&
    formData.weightKg && !isNaN(Number(formData.weightKg)) && Number(formData.weightKg) > 0
  )

  // Calculate recommendation based on biometrics
  const getCalculatedNutrition = () => {
    if (!hasBiometrics) return null
    const weight = Number(formData.weightKg)
    const height = Number(formData.heightCm)
    const age = Number(formData.age)
    const gender = formData.gender.toLowerCase()

    // Mifflin-St Jeor
    const genderFactor = gender === 'female' ? -161 : gender === 'male' ? 5 : -78
    const bmr = 10 * weight + 6.25 * height - 5 * age + genderFactor
    
    // Activity multiplier
    const freq = formData.workoutFrequencyDaysPerWeek
    const mult = freq <= 2 ? 1.2 : freq <= 4 ? 1.375 : freq <= 5 ? 1.55 : 1.725
    const tdee = Math.round(bmr * mult)

    let calories = tdee
    if (formData.primaryGoal === 'fat_loss') calories = Math.max(1200, tdee - 450)
    else if (formData.primaryGoal === 'muscle_gain') calories = tdee + 300
    else if (formData.primaryGoal === 'strength') calories = tdee + 150

    const protein = Math.round(weight * (formData.primaryGoal === 'muscle_gain' ? 2.0 : 1.6))
    const fat = Math.round((calories * 0.25) / 9)
    const carbs = Math.max(50, Math.round((calories - (protein * 4 + fat * 9)) / 4))
    const hydration = Math.round(weight * 0.035 * 10) / 10

    return { calories, protein, carbs, fat, hydration, tdee, bmr }
  }

  const handleApplyCalculated = () => {
    const calc = getCalculatedNutrition()
    if (!calc) return
    setFormData((prev) => ({
      ...prev,
      targetCalories: String(calc.calories),
      targetProteinGrams: String(calc.protein),
      targetCarbsGrams: String(calc.carbs),
      targetFatGrams: String(calc.fat),
      hydrationGoalLiters: String(calc.hydration),
    }))
    showToast('Applied calculated biometric nutrition targets!', 'info')
  }

  const toggleEquipment = (eq: EquipmentType) => {
    setFormData((prev) => {
      const exists = prev.availableEquipment.includes(eq)
      return {
        ...prev,
        availableEquipment: exists
          ? prev.availableEquipment.filter((item) => item !== eq)
          : [...prev.availableEquipment, eq],
      }
    })
  }

  const handleNext = () => {
    setErrorMsg(null)
    if (currentStep === 1) {
      if (!formData.name.trim()) {
        setErrorMsg('Please enter your full name to proceed.')
        return
      }
      if (formData.age && (Number(formData.age) < 13 || Number(formData.age) > 120)) {
        setErrorMsg('Please enter a valid age between 13 and 120, or leave blank.')
        return
      }
      if (formData.heightCm && (Number(formData.heightCm) < 80 || Number(formData.heightCm) > 260)) {
        setErrorMsg('Please enter a valid height in cm, or leave blank.')
        return
      }
      if (formData.weightKg && (Number(formData.weightKg) < 25 || Number(formData.weightKg) > 350)) {
        setErrorMsg('Please enter a valid weight in kg, or leave blank.')
        return
      }
      setCurrentStep(2)
    } else if (currentStep === 2) {
      if (!formData.primaryGoal) {
        setErrorMsg('Please select your primary fitness goal.')
        return
      }
      setCurrentStep(3)
    } else if (currentStep === 3) {
      setCurrentStep(4)
    }
  }

  const handleBack = () => {
    setErrorMsg(null)
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as 1 | 2 | 3 | 4)
    }
  }

  const handleSubmit = async () => {
    setErrorMsg(null)
    try {
      // Build clean payload without empty strings or fictional values
      const payload: Partial<UserProfile> = {
        name: formData.name.trim(),
        profile_complete: true,
        primaryGoal: formData.primaryGoal,
        fitnessLevel: formData.fitnessLevel,
        environment: formData.environment,
        workoutFrequencyDaysPerWeek: Number(formData.workoutFrequencyDaysPerWeek),
        workoutDurationMinutes: Number(formData.workoutDurationMinutes),
        preferredWorkoutType: formData.preferredWorkoutType,
        preferredTrainingTime: formData.preferredTrainingTime,
        availableEquipment: formData.availableEquipment,
      }

      if (formData.gender) payload.gender = formData.gender
      if (formData.age && !isNaN(Number(formData.age))) payload.age = parseInt(formData.age, 10)
      if (formData.heightCm && !isNaN(Number(formData.heightCm))) payload.heightCm = parseFloat(formData.heightCm)
      if (formData.weightKg && !isNaN(Number(formData.weightKg))) payload.weightKg = parseFloat(formData.weightKg)
      if (formData.targetWeightKg && !isNaN(Number(formData.targetWeightKg))) payload.targetWeightKg = parseFloat(formData.targetWeightKg)
      if (formData.dietaryPreference) payload.dietaryPreference = formData.dietaryPreference

      // Nutrition targets - only set if user entered or calculated
      if (formData.targetCalories && !isNaN(Number(formData.targetCalories))) {
        payload.targetCalories = parseInt(formData.targetCalories, 10)
      }
      if (formData.targetProteinGrams && !isNaN(Number(formData.targetProteinGrams))) {
        payload.targetProteinGrams = parseInt(formData.targetProteinGrams, 10)
      }
      if (formData.targetCarbsGrams && !isNaN(Number(formData.targetCarbsGrams))) {
        payload.targetCarbsGrams = parseInt(formData.targetCarbsGrams, 10)
      }
      if (formData.targetFatGrams && !isNaN(Number(formData.targetFatGrams))) {
        payload.targetFatGrams = parseInt(formData.targetFatGrams, 10)
      }
      if (formData.hydrationGoalLiters && !isNaN(Number(formData.hydrationGoalLiters))) {
        payload.hydrationGoalLiters = parseFloat(formData.hydrationGoalLiters)
      }

      await updateProfile(payload)
      showToast('Profile setup complete! Welcome to AI FITNESS.', 'success')
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      console.error('Onboarding submission error:', err)
      setErrorMsg(err.message || 'Failed to save profile. Please check your connection and try again.')
    }
  }

  if (isUserLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <p className="text-xs font-mono text-slate-400">Loading your profile...</p>
        </div>
      </div>
    )
  }

  const calculated = getCalculatedNutrition()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 sm:p-6 lg:p-8">
      {/* Container */}
      <div className="w-full max-w-2xl">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Personalization</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Welcome to <span className="text-emerald-400">AI FITNESS</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-md mx-auto">
            Your AI Fitness Coach — Complete your baseline profile to customize your workouts, nutrition goals, and AI coaching.
          </p>
        </div>

        {/* Step Indicator Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs font-mono mb-2">
            <span className="text-slate-400 font-semibold uppercase tracking-wider">
              Step {currentStep} of 4: {
                currentStep === 1 ? 'Personal Info' :
                currentStep === 2 ? 'Fitness Goals' :
                currentStep === 3 ? 'Training Preferences' : 'Nutrition Targets'
              }
            </span>
            <span className="text-emerald-400 font-medium">{currentStep * 25}% Complete</span>
          </div>
          {/* Progress track */}
          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300 ease-out"
              style={{ width: `${currentStep * 25}%` }}
            />
          </div>

          {/* Stepper bubbles */}
          <div className="grid grid-cols-4 gap-2 mt-3 text-center">
            {[
              { step: 1, label: 'Personal' },
              { step: 2, label: 'Goals' },
              { step: 3, label: 'Training' },
              { step: 4, label: 'Nutrition' },
            ].map((s) => {
              const isPast = currentStep > s.step
              const isCurrent = currentStep === s.step
              return (
                <div
                  key={s.step}
                  className={`flex flex-col items-center gap-1 transition-colors ${
                    isCurrent ? 'text-emerald-400' : isPast ? 'text-slate-300' : 'text-slate-600'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border transition-all ${
                      isPast
                        ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                        : isCurrent
                        ? 'bg-emerald-500 text-slate-950 border-emerald-400 shadow-md shadow-emerald-500/20'
                        : 'bg-slate-900 border-slate-800 text-slate-500'
                    }`}
                  >
                    {isPast ? <Check className="w-3.5 h-3.5" /> : s.step}
                  </div>
                  <span className="text-[11px] font-medium hidden sm:inline">{s.label}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Form Card */}
        <Card className="p-6 sm:p-8 bg-slate-900/90 border border-slate-800 shadow-2xl backdrop-blur-xl relative">
          {errorMsg && (
            <div className="mb-5 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-2.5 text-red-400 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* STEP 1: Personal Information */}
          {currentStep === 1 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="border-b border-slate-800/80 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-400" />
                  Personal Information
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Name is required. Biometrics are completely optional and keep unknown metrics uncalculated.
                </p>
              </div>

              <div className="space-y-4">
                <Input
                  label="Full Name *"
                  placeholder="e.g. Alex Morgan"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5 text-left">
                    <label className="block text-xs font-medium text-slate-300">
                      Gender <span className="text-slate-500 text-[11px] font-normal">(Optional)</span>
                    </label>
                    <select
                      className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      value={formData.gender}
                      onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    >
                      <option value="">Prefer not to say</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="non_binary">Non-binary / Other</option>
                    </select>
                  </div>

                  <Input
                    label="Age (Years)"
                    type="number"
                    placeholder="e.g. 26 (Optional)"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                    min="13"
                    max="120"
                    helperText="Used for metabolic rate estimation"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Height (cm)"
                    type="number"
                    placeholder="e.g. 175 (Optional)"
                    value={formData.heightCm}
                    onChange={(e) => setFormData({ ...formData, heightCm: e.target.value })}
                    min="80"
                    max="260"
                    helperText="Used for BMI and calorie expenditure"
                  />
                  <Input
                    label="Current Weight (kg)"
                    type="number"
                    step="0.1"
                    placeholder="e.g. 74.5 (Optional)"
                    value={formData.weightKg}
                    onChange={(e) => setFormData({ ...formData, weightKg: e.target.value })}
                    min="25"
                    max="350"
                    helperText="Used for protein intake targets"
                  />
                </div>

                <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    Privacy first: Your biometrics are stored securely and never shared. If omitted, biometric fields remain unknown and uncalculated.
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Fitness Goals */}
          {currentStep === 2 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="border-b border-slate-800/80 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Target className="w-4 h-4 text-emerald-400" />
                  Fitness Goals & Experience
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Select your primary fitness objective and current training experience level.
                </p>
              </div>

              {/* Goal Cards */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Primary Fitness Objective *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {GOAL_OPTIONS.map((g) => {
                    const Icon = g.icon
                    const isSelected = formData.primaryGoal === g.id
                    return (
                      <button
                        key={g.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, primaryGoal: g.id })}
                        className={`text-left p-3 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                          isSelected
                            ? 'bg-emerald-500/10 border-emerald-500 shadow-sm shadow-emerald-500/20'
                            : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div
                          className={`p-2 rounded-lg shrink-0 ${
                            isSelected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white flex items-center justify-between">
                            {g.title}
                            {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400 inline ml-1" />}
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{g.desc}</p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Fitness Level */}
              <div className="space-y-2 pt-2">
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Training Experience Level *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {FITNESS_LEVELS.map((lvl) => {
                    const isSelected = formData.fitnessLevel === lvl.id
                    return (
                      <button
                        key={lvl.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, fitnessLevel: lvl.id })}
                        className={`text-left p-3 rounded-xl border transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-500/10 border-emerald-500'
                            : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-bold text-white flex items-center justify-between">
                          {lvl.title}
                          {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 leading-snug">{lvl.subtitle}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Target Weight (Optional) */}
              <div className="pt-2">
                <Input
                  label="Target Weight (kg) - Optional"
                  type="number"
                  step="0.1"
                  placeholder="e.g. 70.0 (Leave blank if not tracking target weight)"
                  value={formData.targetWeightKg}
                  onChange={(e) => setFormData({ ...formData, targetWeightKg: e.target.value })}
                  min="25"
                  max="350"
                  helperText="Optional goal weight for progress tracking"
                />
              </div>
            </div>
          )}

          {/* STEP 3: Training Preferences */}
          {currentStep === 3 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="border-b border-slate-800/80 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Dumbbell className="w-4 h-4 text-emerald-400" />
                  Training Preferences
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Configure your weekly frequency, training environment, and equipment.
                </p>
              </div>

              {/* Environment */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Workout Environment
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: 'gym', label: 'Commercial Gym', sub: 'Full access to barbells, machines & cables' },
                    { id: 'home', label: 'Home Workout', sub: 'Bodyweight, dumbbells, or resistance bands' },
                  ].map((env) => {
                    const isSelected = formData.environment === env.id
                    return (
                      <button
                        key={env.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, environment: env.id as Environment })}
                        className={`text-left p-3 rounded-xl border transition-all cursor-pointer ${
                          isSelected ? 'bg-emerald-500/10 border-emerald-500' : 'bg-slate-950/60 border-slate-800'
                        }`}
                      >
                        <div className="text-xs font-bold text-white flex items-center justify-between">
                          {env.label}
                          {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 leading-snug">{env.sub}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Frequency & Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5 text-left">
                  <label className="block text-xs font-medium text-slate-300">Workouts Per Week</label>
                  <select
                    className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    value={formData.workoutFrequencyDaysPerWeek}
                    onChange={(e) => setFormData({ ...formData, workoutFrequencyDaysPerWeek: Number(e.target.value) })}
                  >
                    <option value={2}>2 Days / Week</option>
                    <option value={3}>3 Days / Week</option>
                    <option value={4}>4 Days / Week (Recommended)</option>
                    <option value={5}>5 Days / Week</option>
                    <option value={6}>6 Days / Week</option>
                  </select>
                </div>

                <div className="space-y-1.5 text-left">
                  <label className="block text-xs font-medium text-slate-300">Session Duration</label>
                  <select
                    className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    value={formData.workoutDurationMinutes}
                    onChange={(e) => setFormData({ ...formData, workoutDurationMinutes: Number(e.target.value) })}
                  >
                    <option value={30}>30 Minutes</option>
                    <option value={45}>45 Minutes</option>
                    <option value={60}>60 Minutes (Standard)</option>
                    <option value={75}>75 Minutes</option>
                    <option value={90}>90 Minutes</option>
                  </select>
                </div>
              </div>

              {/* Equipment Checklist */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Available Equipment
                  </label>
                  <span className="text-[11px] text-slate-400">Select all that apply</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {EQUIPMENT_OPTIONS.map((eq) => {
                    const isSelected = formData.availableEquipment.includes(eq.id)
                    return (
                      <button
                        key={eq.id}
                        type="button"
                        onClick={() => toggleEquipment(eq.id)}
                        className={`p-2 rounded-lg border text-xs text-center transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                          isSelected
                            ? 'bg-emerald-500/15 border-emerald-500/60 text-emerald-300 font-semibold'
                            : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 text-emerald-400 shrink-0" />}
                        <span>{eq.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Nutrition Preferences */}
          {currentStep === 4 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="border-b border-slate-800/80 pb-3">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Utensils className="w-4 h-4 text-emerald-400" />
                  Nutrition Preferences & Targets
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Set your daily calorie and macro goals. Targets can be auto-calculated if biometrics were provided.
                </p>
              </div>

              {/* Dietary Style */}
              <div className="space-y-1.5 text-left">
                <label className="block text-xs font-medium text-slate-300">Dietary Style</label>
                <select
                  className="flex h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  value={formData.dietaryPreference}
                  onChange={(e) => setFormData({ ...formData, dietaryPreference: e.target.value })}
                >
                  <option value="Standard / Balanced">Standard / Balanced</option>
                  <option value="High Protein">High Protein</option>
                  <option value="Vegetarian">Vegetarian</option>
                  <option value="Vegan">Vegan</option>
                  <option value="Keto / Low Carb">Keto / Low Carb</option>
                  <option value="Pescatarian">Pescatarian</option>
                </select>
              </div>

              {/* Auto-calculation Box */}
              {hasBiometrics && calculated ? (
                <div className="rounded-xl bg-gradient-to-br from-emerald-950/40 to-slate-900 border border-emerald-500/30 p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Calculator className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-bold text-emerald-300">Biometric Calorie & Macro Estimate</span>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleApplyCalculated}
                      className="text-xs h-7 px-2.5 bg-emerald-500 text-slate-950 hover:bg-emerald-400 font-semibold"
                    >
                      ⚡ Apply Targets
                    </Button>
                  </div>
                  <p className="text-[11px] text-slate-300">
                    Based on your weight ({formData.weightKg}kg), height ({formData.heightCm}cm), and goal:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                    <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 uppercase">Est. Calories</span>
                      <p className="text-xs font-bold text-emerald-400">{calculated.calories} kcal</p>
                    </div>
                    <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 uppercase">Protein</span>
                      <p className="text-xs font-bold text-cyan-400">{calculated.protein} g</p>
                    </div>
                    <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 uppercase">Carbs</span>
                      <p className="text-xs font-bold text-amber-400">{calculated.carbs} g</p>
                    </div>
                    <div className="bg-slate-950/70 p-2 rounded-lg border border-slate-800 text-center">
                      <span className="text-[10px] text-slate-400 uppercase">Water</span>
                      <p className="text-xs font-bold text-blue-400">{calculated.hydration} L</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3.5 flex items-start gap-2.5 text-xs text-slate-400">
                  <AlertCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-300">No Biometrics Entered:</span> You can manually enter targets below or leave them empty. Targets will not be fabricated without your input.
                  </div>
                </div>
              )}

              {/* Target Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Daily Calorie Target (kcal)"
                  type="number"
                  placeholder="e.g. 2400 (Optional)"
                  value={formData.targetCalories}
                  onChange={(e) => setFormData({ ...formData, targetCalories: e.target.value })}
                  min="500"
                  max="10000"
                  helperText="Leave empty if not tracking daily calories"
                />
                <Input
                  label="Protein Target (grams)"
                  type="number"
                  placeholder="e.g. 150 (Optional)"
                  value={formData.targetProteinGrams}
                  onChange={(e) => setFormData({ ...formData, targetProteinGrams: e.target.value })}
                  min="0"
                  max="500"
                  helperText="Leave empty if not tracking protein"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Input
                  label="Carbs Target (g)"
                  type="number"
                  placeholder="e.g. 250 (Optional)"
                  value={formData.targetCarbsGrams}
                  onChange={(e) => setFormData({ ...formData, targetCarbsGrams: e.target.value })}
                  min="0"
                  max="1000"
                />
                <Input
                  label="Fat Target (g)"
                  type="number"
                  placeholder="e.g. 70 (Optional)"
                  value={formData.targetFatGrams}
                  onChange={(e) => setFormData({ ...formData, targetFatGrams: e.target.value })}
                  min="0"
                  max="400"
                />
                <Input
                  label="Daily Water (Liters)"
                  type="number"
                  step="0.1"
                  placeholder="e.g. 3.0 (Optional)"
                  value={formData.hydrationGoalLiters}
                  onChange={(e) => setFormData({ ...formData, hydrationGoalLiters: e.target.value })}
                  min="0"
                  max="15"
                />
              </div>
            </div>
          )}

          {/* Controls Footer */}
          <div className="mt-8 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
            {currentStep > 1 ? (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                disabled={isUpdating}
                className="text-xs flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </Button>
            ) : (
              <div />
            )}

            {currentStep < 4 ? (
              <Button
                type="button"
                onClick={handleNext}
                className="text-xs flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold px-5"
              >
                Continue
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={isUpdating}
                className="text-xs flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-extrabold px-6 shadow-lg shadow-emerald-500/20"
              >
                {isUpdating ? (
                  <>
                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                    <span>Saving Profile...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Complete Setup & Enter Dashboard</span>
                  </>
                )}
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
