import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from '../api/client'
import type { Progress, ReleaseDetail, ReleaseSummary } from '../api/types'

type AtlasValue = {
  releases: ReleaseSummary[]
  release: ReleaseSummary | undefined
  releaseId: string | undefined
  learnerId: number | undefined
  learnerName: string
  learnerError: ApiError | null
  learnerLoading: boolean
  releaseError: ApiError | null
  dataError: unknown
  releaseLoading: boolean
  isLoadingData: boolean
  topics: Awaited<ReturnType<typeof api.allTopics>>
  hierarchy: Awaited<ReturnType<typeof api.hierarchy>> | undefined
  releaseDetail: ReleaseDetail | undefined
  progress: Progress[]
  progressError: unknown
  selectRelease: (releaseId: string) => Promise<void>
  selectingRelease: boolean
  refreshProgress: () => void
}

const AtlasContext = createContext<AtlasValue | null>(null)

export function AtlasProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const releasesQuery = useQuery({ queryKey: ['releases'], queryFn: api.releases })
  const activeQuery = useQuery({ queryKey: ['active-release'], queryFn: api.activeRelease, retry: false })
  const learnerQuery = useQuery({ queryKey: ['current-learner'], queryFn: api.currentLearner, retry: false })
  const releaseId = activeQuery.data?.release_id
  const learnerId = learnerQuery.data?.learner_id
  const hierarchyQuery = useQuery({ queryKey: ['hierarchy', releaseId], queryFn: () => api.hierarchy(releaseId!), enabled: Boolean(releaseId) })
  const detailQuery = useQuery({ queryKey: ['release-detail', releaseId], queryFn: () => api.releaseDetail(releaseId!), enabled: Boolean(releaseId) })
  const topicsQuery = useQuery({ queryKey: ['topics', releaseId], queryFn: () => api.allTopics(releaseId!), enabled: Boolean(releaseId) })
  const progressQuery = useQuery({ queryKey: ['progress', releaseId, learnerId], queryFn: () => api.progress(releaseId!, learnerId!), enabled: Boolean(releaseId && learnerId) })
  const selectMutation = useMutation({
    mutationFn: api.selectRelease,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['active-release'] })
      await queryClient.invalidateQueries({ queryKey: ['hierarchy'] })
      await queryClient.invalidateQueries({ queryKey: ['release-detail'] })
      await queryClient.invalidateQueries({ queryKey: ['topics'] })
      await queryClient.invalidateQueries({ queryKey: ['progress'] })
    },
  })

  const value = useMemo<AtlasValue>(() => ({
    releases: releasesQuery.data?.items ?? [],
    release: activeQuery.data,
    releaseId,
    learnerId,
    learnerName: learnerQuery.data?.display_name || (learnerId ? 'Personal atlas' : 'Learner unavailable'),
    learnerError: learnerQuery.error instanceof ApiError ? learnerQuery.error : null,
    learnerLoading: learnerQuery.isLoading,
    releaseError: activeQuery.error instanceof ApiError ? activeQuery.error : null,
    dataError: hierarchyQuery.error || topicsQuery.error || detailQuery.error,
    releaseLoading: activeQuery.isLoading || releasesQuery.isLoading,
    isLoadingData: Boolean(releaseId && (hierarchyQuery.isLoading || detailQuery.isLoading || topicsQuery.isLoading || learnerQuery.isLoading || (learnerId && progressQuery.isLoading))),
    topics: topicsQuery.data ?? [],
    hierarchy: hierarchyQuery.data,
    releaseDetail: detailQuery.data,
    progress: progressQuery.data?.items ?? [],
    progressError: progressQuery.error,
    selectRelease: async (id: string) => { await selectMutation.mutateAsync(id) },
    selectingRelease: selectMutation.isPending,
    refreshProgress: () => { void queryClient.invalidateQueries({ queryKey: ['progress', releaseId, learnerId] }) },
  }), [
    releasesQuery.data, releasesQuery.isLoading, activeQuery.data, activeQuery.error, activeQuery.isLoading,
    learnerQuery.data, learnerQuery.error, learnerQuery.isLoading, releaseId, learnerId, hierarchyQuery.data, detailQuery.data,
    hierarchyQuery.isLoading, detailQuery.isLoading, topicsQuery.data, topicsQuery.isLoading,
    hierarchyQuery.error, topicsQuery.error, detailQuery.error,
    progressQuery.data, progressQuery.error, selectMutation.isPending, selectMutation.mutateAsync, queryClient,
  ])

  return <AtlasContext.Provider value={value}>{children}</AtlasContext.Provider>
}

export function useAtlas() {
  const context = useContext(AtlasContext)
  if (!context) throw new Error('useAtlas must be used within AtlasProvider')
  return context
}

export function isNoActiveRelease(error: ApiError | null) {
  return error?.code === 'active_release_not_selected'
}

export function isLearnerAmbiguous(error: ApiError | null) {
  return error?.code === 'current_learner_ambiguous'
}
