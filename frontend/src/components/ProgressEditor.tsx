import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, api } from '../api/client'
import { PROGRESS_STATUSES, type Progress, type ProgressStatus } from '../api/types'
import { useAtlas } from '../app/AtlasContext'

export function ProgressEditor({ topicId, progress }: { topicId: string; progress: Progress | undefined }) {
  const { releaseId, learnerId } = useAtlas()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')
  const mutation = useMutation({
    mutationFn: (patch: { progress_status?: ProgressStatus | null; confidence?: number | null }) => api.patchProgress(releaseId!, learnerId!, topicId, patch),
    onSuccess: async () => {
      setMessage('Assessment saved')
      await queryClient.invalidateQueries({ queryKey: ['progress'] })
      await queryClient.invalidateQueries({ queryKey: ['readiness', releaseId, learnerId, topicId] })
      await queryClient.invalidateQueries({ queryKey: ['progress-topic', releaseId, learnerId, topicId] })
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : 'Could not save this assessment.'),
  })
  const clearMutation = useMutation({
    mutationFn: () => api.clearProgress(releaseId!, learnerId!, topicId),
    onSuccess: async () => {
      setMessage('Assessment cleared · now unassessed')
      await queryClient.invalidateQueries({ queryKey: ['progress'] })
      await queryClient.invalidateQueries({ queryKey: ['readiness', releaseId, learnerId, topicId] })
      await queryClient.invalidateQueries({ queryKey: ['progress-topic', releaseId, learnerId, topicId] })
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : 'Could not clear this assessment.'),
  })
  if (!releaseId || !learnerId) return <div className="assessment-unavailable">Progress controls need an active release and one local learner.</div>

  const setStatus = (value: string) => {
    setMessage('')
    if (!value) {
      if (progress?.confidence == null) clearMutation.mutate()
      else mutation.mutate({ progress_status: null })
    } else mutation.mutate({ progress_status: value as ProgressStatus })
  }
  const setConfidence = (value: string) => {
    setMessage('')
    if (!value) {
      if (progress?.progress_status == null) clearMutation.mutate()
      else mutation.mutate({ confidence: null })
    } else mutation.mutate({ confidence: Number(value) })
  }
  const statusTone = (status: ProgressStatus) => status.toLowerCase().replace(/\s+/g, '-')
  const statusPending = mutation.isPending || clearMutation.isPending

  return <div className="assessment-editor">
    <span className="field-label assessment-editor__status-label">Learning status</span>
    <div className="status-choice-grid" role="group" aria-label="Learning status">
      <button type="button" className={`status-choice status-choice--unassessed${!progress?.progress_status ? ' is-selected' : ''}`} aria-pressed={!progress?.progress_status} disabled={statusPending} onClick={() => { if (progress?.progress_status) setStatus('') }}>Unassessed</button>
      {PROGRESS_STATUSES.map((status) => {
        const selected = progress?.progress_status === status
        return <button type="button" key={status} className={`status-choice status-choice--${statusTone(status)}${selected ? ' is-selected' : ''}`} aria-pressed={selected} disabled={statusPending} onClick={() => { if (!selected) setStatus(status) }}>{status}</button>
      })}
    </div>
    <div className="confidence-heading"><label className="field-label" htmlFor={`confidence-${topicId}`}>Confidence</label><span>{progress?.confidence ? `${progress.confidence} / 5` : 'Not recorded'}</span></div>
    <select id={`confidence-${topicId}`} className="editor-select" value={progress?.confidence ?? ''} disabled={statusPending} onChange={(event) => setConfidence(event.target.value)}>
      <option value="">Not recorded</option>{[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score} · {['','','Developing','Steady','Strong','Deep'][score]}</option>)}
    </select>
    {progress && <button className="clear-assessment" disabled={statusPending} onClick={() => clearMutation.mutate()}>Clear assessment</button>}
    <span className="save-message" aria-live="polite">{statusPending ? 'Saving…' : message}</span>
  </div>
}
