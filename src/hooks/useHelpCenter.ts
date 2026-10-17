import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { helpCenterService } from '../services'

export function useHelpCenter() {
  const [searchQuery, setSearchQuery] = useState('')

  const helpQuery = useQuery({
    queryKey: ['helpCenterData', searchQuery],
    queryFn: () => helpCenterService.searchHelp(searchQuery),
  })

  return {
    helpData: helpQuery.data,
    isLoading: helpQuery.isLoading,
    isError: helpQuery.isError,
    refetch: helpQuery.refetch,
    searchQuery,
    setSearchQuery,
  }
}
