export type ItemList<T> = { items: T[]; next_cursor: string | null }

export type ReleaseSummary = {
  release_id: string
  curriculum_version: string
  schema_version: string
  status: string | null
  imported_at: string
}

export type ReleaseDetail = ReleaseSummary & {
  track_count: number
  phase_count: number
  topic_count: number
}

export type Learner = { learner_id: number; display_name: string | null }
export type Track = { id: string; title: string; metadata: Record<string, unknown> }
export type Phase = { id: string; title: string; metadata: Record<string, unknown> }
export type Objective = { type: string | null; text: string; metadata: Record<string, unknown> }
export type PrerequisiteGroup = { group_ordinal: number; logic_within_group: 'AND'; requires_all: string[] }
export type TopicSummary = {
  id: string
  title: string
  description: string | null
  track_ids: string[]
  phase_id: string | null
  current_priority: string | null
  metadata: Record<string, unknown>
}
export type TopicDetail = TopicSummary & {
  pathway: string | null
  registry_status: string | null
  dependency_review_status: string | null
  objectives: Objective[]
  prerequisite_groups: PrerequisiteGroup[]
  related_topic_ids: string[]
}
export type Hierarchy = {
  release: ReleaseSummary
  tracks: { track: Track; topic_ids: string[] }[]
  phases: { phase: Phase; topic_ids: string[] }[]
}
export type Dependencies = {
  topic_id: string
  prerequisite_groups: PrerequisiteGroup[]
  group_logic: 'OR'
  direct_dependent_ids: string[]
  ancestor_ids: string[]
  downstream_dependent_ids: string[]
  related_topic_ids: string[]
}
export type GroupReadiness = {
  group_ordinal: number
  readiness: 'ready' | 'not_ready' | 'unknown'
  satisfied_topic_ids: string[]
  not_satisfied_topic_ids: string[]
  unknown_topic_ids: string[]
}
export type Readiness = {
  topic_id: string
  readiness: 'ready' | 'not_ready' | 'unknown'
  ready: boolean | null
  has_satisfied_group: boolean
  groups: GroupReadiness[]
}
export type ProgressStatus = 'Not started' | 'Learning' | 'Practicing' | 'Solid' | 'Revisit'
export type Progress = {
  topic_id: string
  progress_status: ProgressStatus | null
  confidence: number | null
  progress_scope: string | null
  notes: string | null
  updated_at: string
}
export type ProgressEnvelope = { progress: Progress | null }

export const PROGRESS_STATUSES: ProgressStatus[] = ['Not started', 'Learning', 'Practicing', 'Solid', 'Revisit']
