/**
 * Authoritative Adaptation Presentation & Formatting Utilities (Phase 9C.5.4).
 *
 * Strictly deterministic, read-only formatting:
 * - Maps backend adaptation types to human-readable labels with neutral fallbacks
 * - Formats rule codes to plain English descriptions
 * - Formats dates safely without throwing
 * - Extracts structured before/after prescription comparisons directly from backend records
 * - Never invents data, calculates progressions, or infers adaptations
 */

export interface AdaptationTypeMeta {
  label: string
  badgeVariant: 'emerald' | 'amber' | 'cyan' | 'indigo' | 'slate'
}

/**
 * Deterministic mapping of backend adaptation types to UI display metadata.
 * Unknown future values safely fall back to neutral "Adaptive Update".
 */
export function formatAdaptationType(type?: string | null): AdaptationTypeMeta {
  if (!type || typeof type !== 'string') {
    return { label: 'Adaptive Update', badgeVariant: 'cyan' }
  }

  const normalized = type.toLowerCase().trim()
  switch (normalized) {
    case 'double_progression':
      return { label: 'Double Progression', badgeVariant: 'emerald' }
    case 'volume_reduction':
      return { label: 'Volume Reduction', badgeVariant: 'amber' }
    case 'split_adjustment':
      return { label: 'Split Adjustment', badgeVariant: 'indigo' }
    case 'form_correction':
      return { label: 'Form Correction', badgeVariant: 'cyan' }
    default:
      // Neutral fallback for any unknown future backend type
      return {
        label: normalized
          .split('_')
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ') || 'Adaptive Update',
        badgeVariant: 'cyan',
      }
  }
}

/**
 * Deterministically formats Phase 9C.2 backend rule codes.
 */
export function formatRuleCode(ruleCode?: string | null): string {
  if (!ruleCode || typeof ruleCode !== 'string') {
    return 'Prescription Adaptation'
  }

  const code = ruleCode.toUpperCase().trim()
  switch (code) {
    case 'DOUBLE_PROGRESSION_UPPER_COMPOUND':
      return 'Upper Body Load Progression (+2.5 kg)'
    case 'DOUBLE_PROGRESSION_LOWER_COMPOUND':
      return 'Lower Body Load Progression (+5.0 kg)'
    case 'DOUBLE_PROGRESSION_ISOLATION':
      return 'Isolation Load Progression (+1.0 kg)'
    case 'DOUBLE_PROGRESSION_BODYWEIGHT':
      return 'Bodyweight Rep Progression (+1 rep)'
    case 'VOLUME_FATIGUE_2_SESSIONS':
      return 'Volume Fatigue Management (-1 Set)'
    case 'ADHERENCE_SPLIT_MISMATCH_4_WEEKS':
      return 'Adherence Split Recommendation'
    case 'RECURRING_FORM_COMPENSATION':
      return 'Form Technique Adjustment'
    default:
      // Format screaming snake case to readable text
      return code
        .split('_')
        .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
        .join(' ')
  }
}

/**
 * Formats ISO timestamps into human-readable date/time strings.
 * Safe against empty, invalid, or malformed strings.
 */
export function formatAdaptationDate(isoString?: string | null): string {
  if (!isoString || typeof isoString !== 'string') return 'Recently'
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return 'Recently'

    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(d)
  } catch {
    return 'Recently'
  }
}

export interface MetricComparison {
  metric: string
  before: string
  after: string
}

/**
 * Formats before/after prescription deltas from authoritative backend records.
 * Never calculates deltas; renders existing values directly.
 */
export function extractMetricComparisons(
  previousPrescription?: Record<string, any> | null,
  appliedPrescription?: Record<string, any> | null
): MetricComparison[] {
  const comparisons: MetricComparison[] = []
  if (!previousPrescription && !appliedPrescription) return comparisons

  const prev = previousPrescription || {}
  const appl = appliedPrescription || {}

  // 1. Weight / Load
  const prevWt = prev.weightKg ?? prev.weight_kg ?? prev.targetWeightKg ?? prev.target_weight_kg
  const applWt = appl.weightKg ?? appl.weight_kg ?? appl.targetWeightKg ?? appl.target_weight_kg ?? appl.adaptedWeightKg ?? appl.adapted_weight_kg

  if (prevWt !== undefined && applWt !== undefined && prevWt !== null && applWt !== null) {
    comparisons.push({
      metric: 'Load',
      before: `${prevWt} kg`,
      after: `${applWt} kg`,
    })
  }

  // 2. Set Count
  const prevSets = prev.setCount ?? prev.set_count ?? prev.totalSets ?? prev.total_sets
  const applSets = appl.setCount ?? appl.set_count ?? appl.totalSets ?? appl.total_sets ?? appl.adaptedSetCount

  if (prevSets !== undefined && applSets !== undefined && prevSets !== null && applSets !== null) {
    comparisons.push({
      metric: 'Sets',
      before: `${prevSets} sets`,
      after: `${applSets} sets`,
    })
  }

  // 3. Reps
  const prevReps = prev.targetReps ?? prev.target_reps ?? (prev.targetRepsMax ? `${prev.targetRepsMin || 8}–${prev.targetRepsMax}` : null)
  const applReps = appl.targetReps ?? appl.target_reps ?? (appl.targetRepsMax ? `${appl.targetRepsMin || 8}–${appl.targetRepsMax}` : null)

  if (prevReps && applReps && prevReps !== applReps) {
    comparisons.push({
      metric: 'Reps',
      before: `${prevReps} reps`,
      after: `${applReps} reps`,
    })
  }

  return comparisons
}

/**
 * Formats canonical exercise IDs to human-readable names.
 */
export function formatExerciseDisplayName(exerciseId?: string | null): string {
  if (!exerciseId || typeof exerciseId !== 'string') return 'Exercise'
  return exerciseId
    .replace(/^ex_/, '')
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Formats list of affected days into compact description.
 */
export function formatAffectedDays(
  affectedDays?: Array<{ weekNumber?: number; week_number?: number; dayNumber?: number; day_number?: number }> | null
): string {
  if (!affectedDays || affectedDays.length === 0) return ''
  return affectedDays
    .map((ad) => {
      const w = ad.weekNumber ?? ad.week_number ?? 1
      const d = ad.dayNumber ?? ad.day_number ?? 1
      return `W${w}D${d}`
    })
    .join(', ')
}
