import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProfile, useUser } from '../../hooks'
import { ProfileHeader } from '../../components/profile/ProfileHeader'
import { ProfileTabs } from '../../components/profile/ProfileTabs'
import { ProfileHeroCard } from '../../components/profile/ProfileHeroCard'
import { PersonalInformationCard } from '../../components/profile/PersonalInformationCard'
import { FitnessGoalsCard } from '../../components/profile/FitnessGoalsCard'
import { PersonalStatsCard } from '../../components/profile/PersonalStatsCard'
import { TrainingPreferencesCard } from '../../components/profile/TrainingPreferencesCard'
import { NutritionPreferencesCard } from '../../components/profile/NutritionPreferencesCard'
import { AchievementsSummaryCard } from '../../components/profile/AchievementsSummaryCard'
import { RecentBadgesCard } from '../../components/profile/RecentBadgesCard'
import { AccountPreferencesCard } from '../../components/profile/AccountPreferencesCard'
import { EditProfileModal } from '../../components/profile/EditProfileModal'
import { EditGoalModal } from '../../components/profile/EditGoalModal'
import { PreferenceModal } from '../../components/profile/PreferenceModal'
import { Skeleton, ErrorState } from '../../components/ui'

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useUser()
  const { profile, isLoading, isError, refetch, updateProfile, updateGoal } = useProfile()

  const [activeTab, setActiveTab] = useState('Overview')
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false)
  const [isEditGoalOpen, setIsEditGoalOpen] = useState(false)
  const [prefModalTitle, setPrefModalTitle] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !profile) {
    return (
      <ErrorState
        title="Profile Data Unavailable"
        message="Could not load personal profile information. Please try again."
        onRetry={refetch}
      />
    )
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Incomplete Profile Setup Banner */}
      {user && user.profile_complete === false && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-amber-300">Profile Setup Incomplete</h3>
            <p className="text-xs text-slate-300">
              Complete your personalized onboarding to set your fitness goals, biometric targets, and workout preferences.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/onboarding')}
            className="shrink-0 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 text-xs font-extrabold hover:brightness-110 shadow-lg shadow-emerald-500/20 cursor-pointer"
          >
            Complete Profile Setup →
          </button>
        </div>
      )}

      {/* Top Header */}
      <ProfileHeader onEditProfileClick={() => setIsEditProfileOpen(true)} />

      {/* Sub-Header Navigation Tabs */}
      <ProfileTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Profile Hero Card (Full Width) */}
      <ProfileHeroCard
        hero={profile.hero}
        onEditAvatarClick={() => setIsEditProfileOpen(true)}
      />

      {/* Row 2: Personal Information, Fitness Goals & Personal Stats (3 Equal Columns) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PersonalInformationCard info={profile.personalInfo} />
        <FitnessGoalsCard goals={profile.goals} onEditGoalClick={() => setIsEditGoalOpen(true)} />
        <PersonalStatsCard stats={profile.stats} />
      </div>

      {/* Row 3: Training Preferences, Nutrition Preferences & Achievements Summary (3 Equal Columns) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <TrainingPreferencesCard
          pref={profile.trainingPref}
          onEditClick={() => setPrefModalTitle('Edit Training Preferences')}
        />
        <NutritionPreferencesCard
          pref={profile.nutritionPref}
          onEditClick={() => setPrefModalTitle('Edit Nutrition Preferences')}
        />
        <AchievementsSummaryCard
          onViewAllClick={() => alert('Viewing all achievements')}
          totalBadges={0}
          totalPoints={profile.hero.totalPoints || 0}
          rank={profile.hero.rankPct || 'Unranked'}
        />
      </div>

      {/* Row 4: Recent Badges Earned & Account & Preferences (2 Columns: 8 & 4) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <RecentBadgesCard onViewAllClick={() => alert('Viewing recent badges')} badges={[]} />
        </div>
        <div className="lg:col-span-4">
          <AccountPreferencesCard
            rows={profile.accountRows}
            onManageClick={() => setPrefModalTitle('Manage Account & Preferences')}
            onRowClick={(id) => setPrefModalTitle(`Settings: ${id}`)}
          />
        </div>
      </div>

      {/* Edit Profile Modal */}
      <EditProfileModal
        isOpen={isEditProfileOpen}
        onClose={() => setIsEditProfileOpen(false)}
        currentInfo={profile.personalInfo}
        name={profile.hero.name}
        onSave={(data) => updateProfile(data)}
      />

      {/* Edit Goal Modal */}
      <EditGoalModal
        isOpen={isEditGoalOpen}
        onClose={() => setIsEditGoalOpen(false)}
        currentGoal={profile.goals}
        onSave={(data) => updateGoal(data)}
      />

      {/* Preferences Modal */}
      <PreferenceModal
        isOpen={Boolean(prefModalTitle)}
        onClose={() => setPrefModalTitle(null)}
        title={prefModalTitle || 'Preferences'}
      />
    </div>
  )
}
