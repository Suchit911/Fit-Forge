import { useState, useEffect, useCallback } from 'react'
import type { FormAnalysisSessionSummary } from '../types/formStream'
import { formAnalysisService } from '../services/formAnalysisService'

interface UseFormAnalysisHistoryOptions {
  limit?: number
  exerciseId?: string
  autoFetch?: boolean
}

export interface UseFormAnalysisHistoryReturn {
  history: FormAnalysisSessionSummary[]
  loading: boolean
  error: string | null
  refetchHistory: () => Promise<void>
}

export function useFormAnalysisHistory(
  options: UseFormAnalysisHistoryOptions = {}
): UseFormAnalysisHistoryReturn {
  const { limit = 20, exerciseId, autoFetch = true } = options
  const [history, setHistory] = useState<FormAnalysisSessionSummary[]>([])
  const [loading, setLoading] = useState<boolean>(autoFetch)
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await formAnalysisService.getHistory(limit, exerciseId)
      setHistory(data)
    } catch (err: any) {
      console.error('Error loading form analysis history:', err)
      setError(err?.message || 'Failed to load form analysis history.')
      setHistory([])
    } finally {
      setLoading(false)
    }
  }, [limit, exerciseId])

  useEffect(() => {
    if (autoFetch) {
      fetchHistory()
    }
  }, [fetchHistory, autoFetch])

  return {
    history,
    loading,
    error,
    refetchHistory: fetchHistory,
  }
}
