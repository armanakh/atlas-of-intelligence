import type {
  Dependencies, Hierarchy, ItemList, Learner, Progress, ProgressEnvelope, ProgressStatus,
  Readiness, ReleaseDetail, ReleaseSummary, TopicDetail, TopicSummary,
} from './types'
import { collectAllPages } from './pagination'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details: Record<string, unknown> = {},
  ) { super(message); this.name = 'ApiError' }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch {
    throw new ApiError('Could not reach the local curriculum API.', 0, 'api_unavailable')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const error = body?.error
    throw new ApiError(
      error?.message || `The request failed (${response.status}).`,
      response.status,
      error?.code || 'request_failed',
      error?.details || {},
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  releases: () => request<ItemList<ReleaseSummary>>('/api/v1/curriculum/releases'),
  activeRelease: () => request<ReleaseSummary>('/api/v1/curriculum/active-release'),
  selectRelease: (releaseId: string) => request<ReleaseSummary>('/api/v1/curriculum/active-release', {
    method: 'PUT', body: JSON.stringify({ release_id: releaseId }),
  }),
  releaseDetail: (releaseId: string) => request<ReleaseDetail>(`/api/v1/curriculum/releases/${releaseId}`),
  hierarchy: (releaseId: string) => request<Hierarchy>(`/api/v1/curriculum/releases/${releaseId}/hierarchy`),
  async allTopics(releaseId: string, filters: { track_id?: string; phase_id?: string } = {}) {
    return collectAllPages<TopicSummary>(async (cursor) => {
      const params = new URLSearchParams({ limit: '200' })
      if (filters.track_id) params.set('track_id', filters.track_id)
      if (filters.phase_id) params.set('phase_id', filters.phase_id)
      if (cursor) params.set('cursor', cursor)
      return request<ItemList<TopicSummary>>(`/api/v1/curriculum/releases/${releaseId}/topics?${params}`)
    })
  },
  topic: (releaseId: string, topicId: string) => request<TopicDetail>(`/api/v1/curriculum/releases/${releaseId}/topics/${encodeURIComponent(topicId)}`),
  dependencies: (releaseId: string, topicId: string) => request<Dependencies>(`/api/v1/curriculum/releases/${releaseId}/topics/${encodeURIComponent(topicId)}/dependencies`),
  currentLearner: () => request<Learner>('/api/v1/learners/current'),
  progress: (releaseId: string, learnerId: number) => request<ItemList<Progress>>(`/api/v1/curriculum/releases/${releaseId}/learners/${learnerId}/progress`),
  progressForTopic: (releaseId: string, learnerId: number, topicId: string) => request<ProgressEnvelope>(`/api/v1/curriculum/releases/${releaseId}/learners/${learnerId}/progress/${encodeURIComponent(topicId)}`),
  readiness: (releaseId: string, learnerId: number, topicId: string) => request<Readiness>(`/api/v1/curriculum/releases/${releaseId}/learners/${learnerId}/topics/${encodeURIComponent(topicId)}/readiness`),
  patchProgress: (releaseId: string, learnerId: number, topicId: string, patch: { progress_status?: ProgressStatus | null; confidence?: number | null }) => request<ProgressEnvelope>(`/api/v1/curriculum/releases/${releaseId}/learners/${learnerId}/progress/${encodeURIComponent(topicId)}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  clearProgress: (releaseId: string, learnerId: number, topicId: string) => request<void>(`/api/v1/curriculum/releases/${releaseId}/learners/${learnerId}/progress/${encodeURIComponent(topicId)}`, { method: 'DELETE' }),
}

export function isApiError(error: unknown): error is ApiError { return error instanceof ApiError }
