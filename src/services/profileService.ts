import type { ProfileDashboardData } from '../types'
import { userService } from './userService'

function formatGoal(goal?: string): string {
  if (!goal) return ''
  switch (goal) {
    case 'muscle_gain':
      return 'Build Muscle'
    case 'fat_loss':
      return 'Fat Loss'
    case 'strength':
      return 'Pure Strength'
    case 'endurance':
      return 'Endurance'
    case 'general_fitness':
      return 'General Fitness'
    default:
      return goal.replace(/_/g, ' ')
  }
}

function getBmiStatus(bmi: number): string {
  if (bmi <= 0) return 'Not Calculated'
  if (bmi < 18.5) return 'Underweight'
  if (bmi < 25) return 'Healthy'
  if (bmi < 30) return 'Overweight'
  return 'Obese'
}

export const profileService = {
  /**
   * Retrieves profile dashboard data derived strictly from the authenticated user's real Firestore profile.
   */
  async getProfileData(): Promise<ProfileDashboardData> {
    const user = await userService.getUserProfile()

    const bmi = user.bmi || (user.heightCm && user.weightKg ? Math.round((user.weightKg / Math.pow(user.heightCm / 100, 2)) * 10) / 10 : 0)
    const targetWt = user.targetWeightKg || user.weightKg || 0
    const kgToGo = user.weightKg && user.targetWeightKg ? Math.round(Math.abs(user.weightKg - user.targetWeightKg) * 10) / 10 : 0

    return {
      hero: {
        name: user.name,
        verified: true,
        plan: 'Member Tier',
        memberSince: 'Member',
        location: 'Personal Account',
        quote: '"Consistency today, strength tomorrow."',
        streakDays: user.streakDays || 0,
        totalWorkouts: user.totalWorkouts || 0,
        totalCaloriesBurned: user.totalCaloriesBurned || 0,
        totalPoints: user.totalPoints || 0,
        rankPct: user.totalPoints ? 'Active Lifter' : 'Unranked',
        avatarUrl: '/assets/hero_trainer.jpg',
      },
      personalInfo: {
        age: user.age || 0,
        heightCm: user.heightCm || 0,
        weightKg: user.weightKg || 0,
        fitnessGoal: formatGoal(user.primaryGoal) || (user.profile_complete ? 'General Fitness' : 'Not set'),
        activityLevel: user.fitnessLevel ? user.fitnessLevel.charAt(0).toUpperCase() + user.fitnessLevel.slice(1) : (user.profile_complete ? 'Moderate' : 'Not set'),
      },
      goals: {
        primaryGoal: formatGoal(user.primaryGoal) || (user.profile_complete ? 'General Fitness' : 'Not set'),
        targetWeightKg: targetWt,
        weeklyWorkoutTarget: user.workoutFrequencyDaysPerWeek ? `${user.workoutFrequencyDaysPerWeek} days / week` : 'Not set',
        targetDate: 'Active Target',
        progressPct: user.totalWorkouts ? Math.min(100, Math.round((user.totalWorkouts / 20) * 100)) : 0,
        kgToGo: kgToGo,
      },
      stats: {
        currentWeightKg: user.weightKg || 0,
        weightChangeKg: 0.0,
        bodyFatPct: 0.0,
        bodyFatChangePct: 0.0,
        muscleMassKg: 0.0,
        muscleMassChangeKg: 0.0,
        bmi: bmi,
        bmiStatus: getBmiStatus(bmi),
      },
      trainingPref: {
        trainingDays: user.workoutFrequencyDaysPerWeek ? `${user.workoutFrequencyDaysPerWeek} days per week` : 'Not set',
        preferredWorkoutType: user.preferredWorkoutType || (user.primaryGoal ? formatGoal(user.primaryGoal) : 'Not set'),
        equipmentAvailable: user.availableEquipment && user.availableEquipment.length > 0
          ? user.availableEquipment.map((e) => e.replace(/_/g, ' ')).join(', ')
          : (user.environment ? (user.environment === 'gym' ? 'Gym Equipment' : 'Home Equipment') : 'Not set'),
        workoutDuration: user.workoutDurationMinutes ? `${user.workoutDurationMinutes} minutes` : 'Not set',
        preferredTime: user.preferredTrainingTime || 'Not set',
      },
      nutritionPref: {
        dietaryPreference: user.dietaryPreference || 'Not set',
        dailyCalorieTarget: user.targetCalories || 0,
        proteinTargetGrams: user.targetProteinGrams || 0,
        carbTargetGrams: user.targetCarbsGrams || 0,
        hydrationGoalLiters: user.hydrationGoalLiters || 0,
      },
      accountRows: [
        { id: 'acc_1', title: 'Notifications', description: 'Manage your notification preferences', iconName: 'bell' },
        { id: 'acc_2', title: 'Privacy & Security', description: 'Manage your privacy and security settings', iconName: 'lock' },
        { id: 'acc_3', title: 'Connected Devices', description: 'Manage your connected devices', iconName: 'smartphone' },
      ],
    }
  },

  async updateProfileInfo(name: string, age: number, heightCm: number, weightKg: number, fitnessGoal: string, activityLevel: string): Promise<ProfileDashboardData> {
    await userService.updateUserProfile({
      name,
      age,
      heightCm,
      weightKg,
      primaryGoal: fitnessGoal as any,
      fitnessLevel: activityLevel.toLowerCase().includes('adv') ? 'advanced' : activityLevel.toLowerCase().includes('beg') ? 'beginner' : 'intermediate',
    })
    return this.getProfileData()
  },

  async updateGoal(primaryGoal: string, targetWeightKg: number, weeklyTarget: string, _targetDate: string): Promise<ProfileDashboardData> {
    const daysMatch = weeklyTarget.match(/\d+/)
    const days = daysMatch ? parseInt(daysMatch[0], 10) : undefined

    await userService.updateUserProfile({
      targetWeightKg,
      workoutFrequencyDaysPerWeek: days,
      primaryGoal: primaryGoal as any,
    })
    return this.getProfileData()
  },
}
