import type { Phase, Progress, ProgressStatus, TopicSummary, Track } from '../../api/types'
import { buildAtlasSurveyModel, type AtlasField, type AtlasIdea } from '../atlas/atlasModel.ts'

export const PROGRESS_CHAPTERS = [
  {
    id: 'foundations',
    number: '01',
    title: 'Foundations',
    purpose: 'Establish the ability to reason computationally and build software.',
    fieldIds: ['PH00', 'PH01', 'PH02', 'PH03'],
  },
  {
    id: 'machinery',
    number: '02',
    title: 'Mathematical and Computational Machinery',
    purpose: 'Build the mathematical and computational foundations behind machine learning.',
    fieldIds: ['PH04', 'PH05', 'PH06', 'PH07', 'PH08'],
  },
  {
    id: 'machine-learning',
    number: '03',
    title: 'Machine Learning',
    purpose: 'Understand how machine learning models learn.',
    fieldIds: ['PH09', 'PH10'],
  },
  {
    id: 'modern-ai',
    number: '04',
    title: 'Modern AI',
    purpose: 'Explore modern learning architectures and generative AI systems.',
    fieldIds: ['PH11', 'PH12', 'PH13'],
  },
  {
    id: 'engineering-intelligence',
    number: '05',
    title: 'Engineering and Advanced Intelligence',
    purpose: 'Develop operational systems, intelligent agents and advanced research capability.',
    fieldIds: ['PH14', 'PH15', 'PH16'],
  },
] as const

export type JourneyStatus = ProgressStatus | 'Unassessed'
export const JOURNEY_STATUSES: readonly JourneyStatus[] = [
  'Solid', 'Learning', 'Practicing', 'Revisit', 'Not started', 'Unassessed',
]

export type StatusCounts = Record<JourneyStatus, number>
export type JourneyIdea = AtlasIdea & {
  progressStatus: JourneyStatus
  confidence: number | null
  hasProgressRecord: boolean
}

export type JourneyField = Omit<AtlasField, 'ideas'> & {
  chapterId: string
  ideas: readonly JourneyIdea[]
  counts: StatusCounts
  assessedCount: number
  unassessedCount: number
  confidenceOnlyCount: number
  solidShare: number
}

export type JourneyChapter = {
  id: string
  number: string
  title: string
  purpose: string
  fields: readonly JourneyField[]
  counts: StatusCounts
  ideaCount: number
  assessedCount: number
  unassessedCount: number
}

export type ProgressJourney = {
  chapters: readonly JourneyChapter[]
  fields: readonly JourneyField[]
  ideaCount: number
  counts: StatusCounts
  assessedCount: number
  unassessedCount: number
  progressRecordCount: number
  confidenceOnlyCount: number
  solidShare: number
}

export type ProgressJourneySource = {
  tracks: readonly Track[]
  phases: readonly Phase[]
  topics: readonly TopicSummary[]
  progress: readonly Progress[]
  complete: boolean
}

function emptyCounts(): StatusCounts {
  return { Solid: 0, Learning: 0, Practicing: 0, Revisit: 0, 'Not started': 0, Unassessed: 0 }
}

function addCounts(target: StatusCounts, source: StatusCounts) {
  for (const status of JOURNEY_STATUSES) target[status] += source[status]
}

/** Derives a release-scoped journey without creating or changing learner records. */
export function buildProgressJourney(source: ProgressJourneySource): ProgressJourney {
  const atlas = buildAtlasSurveyModel({
    tracks: source.tracks,
    phases: source.phases,
    topics: source.topics,
    complete: source.complete,
  })
  if (atlas.unplacedIdeas.length) {
    throw new Error(`Progress journey requires a Field placement for every Idea; ${atlas.unplacedIdeas.length} are unplaced.`)
  }

  const chapterForField = new Map<string, (typeof PROGRESS_CHAPTERS)[number]>()
  for (const chapter of PROGRESS_CHAPTERS) {
    for (const fieldId of chapter.fieldIds) {
      if (chapterForField.has(fieldId)) throw new Error(`Field ${fieldId} appears in more than one chapter.`)
      chapterForField.set(fieldId, chapter)
    }
  }
  for (const field of atlas.fields) {
    if (!chapterForField.has(field.id)) throw new Error(`No Progress chapter is defined for Field ${field.id}.`)
  }

  const progressByTopic = new Map<string, Progress>()
  for (const row of source.progress) {
    if (progressByTopic.has(row.topic_id)) throw new Error(`Duplicate learner progress record for Idea ${row.topic_id}.`)
    progressByTopic.set(row.topic_id, row)
  }

  const fields: JourneyField[] = atlas.fields.map((field) => {
    const chapter = chapterForField.get(field.id)!
    const counts = emptyCounts()
    let assessedCount = 0
    let confidenceOnlyCount = 0
    const ideas: JourneyIdea[] = field.ideas.map((idea) => {
      const row = progressByTopic.get(idea.id)
      const status = row?.progress_status ?? 'Unassessed'
      counts[status] += 1
      if (row?.progress_status) assessedCount += 1
      if (row && row.progress_status == null && row.confidence != null) confidenceOnlyCount += 1
      return {
        ...idea,
        progressStatus: status,
        confidence: row?.confidence ?? null,
        hasProgressRecord: row !== undefined,
      }
    })
    return {
      ...field,
      chapterId: chapter.id,
      ideas,
      counts,
      assessedCount,
      unassessedCount: counts.Unassessed,
      confidenceOnlyCount,
      solidShare: field.ideaCount ? counts.Solid / field.ideaCount : 0,
    }
  })

  const chapterList: JourneyChapter[] = PROGRESS_CHAPTERS.map((chapter) => {
    const chapterFields = fields.filter((field) => field.chapterId === chapter.id)
    const counts = emptyCounts()
    for (const field of chapterFields) addCounts(counts, field.counts)
    return {
      id: chapter.id,
      number: chapter.number,
      title: chapter.title,
      purpose: chapter.purpose,
      fields: chapterFields,
      counts,
      ideaCount: chapterFields.reduce((sum, field) => sum + field.ideaCount, 0),
      assessedCount: chapterFields.reduce((sum, field) => sum + field.assessedCount, 0),
      unassessedCount: chapterFields.reduce((sum, field) => sum + field.unassessedCount, 0),
    }
  })

  const counts = emptyCounts()
  for (const field of fields) addCounts(counts, field.counts)
  const ideaCount = atlas.ideas.length
  const assessedCount = JOURNEY_STATUSES.filter((status) => status !== 'Unassessed')
    .reduce((sum, status) => sum + counts[status], 0)
  return {
    chapters: chapterList,
    fields,
    ideaCount,
    counts,
    assessedCount,
    unassessedCount: counts.Unassessed,
    progressRecordCount: progressByTopic.size,
    confidenceOnlyCount: fields.reduce((sum, field) => sum + field.confidenceOnlyCount, 0),
    solidShare: ideaCount ? counts.Solid / ideaCount : 0,
  }
}

export function progressPercent(value: number, total: number): string {
  if (!total) return '0%'
  return `${(value / total * 100).toFixed(1).replace(/\.0$/, '')}%`
}
