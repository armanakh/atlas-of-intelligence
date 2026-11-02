import test from 'node:test'
import assert from 'node:assert/strict'
import type { Phase, Progress, TopicSummary, Track } from '../src/api/types.ts'
import { PROGRESS_CHAPTERS, buildProgressJourney, progressPercent } from '../src/features/progress/progressModel.ts'

const tracks: Track[] = [
  { id: 'TR-CS', title: 'Computer Science', metadata: {} },
  { id: 'TR-MATH', title: 'Mathematics', metadata: {} },
]

const phases: Phase[] = PROGRESS_CHAPTERS.flatMap((chapter) => chapter.fieldIds.map((id) => ({ id, title: id, metadata: {} })))

function topic(id: string, phaseId: string, trackIds: string[] = ['TR-CS']): TopicSummary {
  return { id, title: `Idea ${id}`, description: `Description ${id}`, phase_id: phaseId, track_ids: trackIds, current_priority: null, metadata: {} }
}

function progress(topicId: string, progressStatus: Progress['progress_status'], confidence: number | null = null): Progress {
  return { topic_id: topicId, progress_status: progressStatus, confidence, progress_scope: null, notes: null, updated_at: '2026-11-02T00:00:00Z' }
}

test('preserves source Field order and assigns each Field to one of the five presentation chapters', () => {
  const inputPhases = [...phases]
  const journey = buildProgressJourney({ tracks, phases: inputPhases, topics: [], progress: [], complete: true })
  const expectedOrder = phases.map((phase) => phase.id)
  assert.deepEqual(journey.fields.map((field) => field.id), expectedOrder)
  assert.deepEqual(journey.chapters.map((chapter) => chapter.id), PROGRESS_CHAPTERS.map((chapter) => chapter.id))
  assert.deepEqual(journey.chapters.flatMap((chapter) => chapter.fields.map((field) => field.id)), expectedOrder)
  assert.equal(journey.chapters.length, 5)
  assert.equal(journey.fields.length, 17)
})

test('retains canonical Idea identity and overlapping Territory affiliations without duplication', () => {
  const ideas = [topic('A', 'PH00', ['TR-CS', 'TR-MATH']), topic('B', 'PH00')]
  const journey = buildProgressJourney({ tracks, phases, topics: ideas, progress: [], complete: true })
  const field = journey.fields[0]
  assert.equal(journey.ideaCount, 2)
  assert.equal(field.ideaCount, 2)
  assert.equal(field.ideas.filter((idea) => idea.id === 'A').length, 1)
  assert.deepEqual(field.ideas[0].territoryIds, ['TR-CS', 'TR-MATH'])
  assert.equal(field.territoryIntersections.find(({ territoryId }) => territoryId === 'TR-CS')?.ideaCount, 2)
  assert.equal(field.territoryIntersections.find(({ territoryId }) => territoryId === 'TR-MATH')?.ideaCount, 1)
})

test('summarizes every learner state while keeping missing records and confidence-only records unassessed', () => {
  const ideas = [
    topic('solid', 'PH00'), topic('learning', 'PH00'), topic('practicing', 'PH00'),
    topic('revisit', 'PH00'), topic('not-started', 'PH00'), topic('missing', 'PH00'), topic('confidence-only', 'PH00'),
  ]
  const rows = [
    progress('solid', 'Solid', 2), progress('learning', 'Learning'), progress('practicing', 'Practicing'),
    progress('revisit', 'Revisit'), progress('not-started', 'Not started'), progress('confidence-only', null, 4),
  ]
  const before = JSON.stringify({ ideas, rows })
  const journey = buildProgressJourney({ tracks, phases, topics: ideas, progress: rows, complete: true })
  const field = journey.fields[0]
  assert.deepEqual(field.counts, { Solid: 1, Learning: 1, Practicing: 1, Revisit: 1, 'Not started': 1, Unassessed: 2 })
  assert.equal(field.assessedCount, 5)
  assert.equal(field.unassessedCount, 2)
  assert.equal(field.confidenceOnlyCount, 1)
  assert.equal(journey.assessedCount, 5)
  assert.equal(journey.unassessedCount, 2)
  assert.equal(journey.progressRecordCount, 6)
  assert.equal(journey.confidenceOnlyCount, 1)
  assert.equal(journey.solidShare, 1 / 7)
  assert.equal(field.ideas.find((idea) => idea.id === 'missing')?.progressStatus, 'Unassessed')
  assert.equal(field.ideas.find((idea) => idea.id === 'missing')?.hasProgressRecord, false)
  assert.equal(field.ideas.find((idea) => idea.id === 'confidence-only')?.progressStatus, 'Unassessed')
  assert.equal(field.ideas.find((idea) => idea.id === 'confidence-only')?.confidence, 4)
  assert.equal(JSON.stringify({ ideas, rows }), before)
  assert.equal(progressPercent(1, 7), '14.3%')
})

test('derives accurate chapter and whole-journey totals from Field Ideas', () => {
  const ideas = [topic('a', 'PH00'), topic('b', 'PH03'), topic('c', 'PH04'), topic('d', 'PH16')]
  const rows = [progress('a', 'Solid'), progress('c', 'Practicing'), progress('d', 'Not started')]
  const journey = buildProgressJourney({ tracks, phases, topics: ideas, progress: rows, complete: true })
  assert.equal(journey.ideaCount, 4)
  assert.equal(journey.counts.Solid, 1)
  assert.equal(journey.counts.Practicing, 1)
  assert.equal(journey.counts['Not started'], 1)
  assert.equal(journey.counts.Unassessed, 1)
  assert.deepEqual(journey.chapters.map(({ ideaCount }) => ideaCount), [2, 1, 0, 0, 1])
  assert.equal(journey.chapters[0].counts.Solid, 1)
  assert.equal(journey.chapters[4].counts['Not started'], 1)
  assert.equal(journey.fields.reduce((sum, field) => sum + field.ideaCount, 0), journey.ideaCount)
})

test('rejects duplicate progress rows, missing chapter assignments, unplaced Ideas and incomplete data', () => {
  const a = topic('a', 'PH00')
  assert.throws(() => buildProgressJourney({ tracks, phases, topics: [a, a], progress: [], complete: true }), /Duplicate Topic identity/)
  assert.throws(() => buildProgressJourney({ tracks, phases: [...phases, { id: 'PH99', title: 'Future', metadata: {} }], topics: [], progress: [], complete: true }), /No Progress chapter/)
  assert.throws(() => buildProgressJourney({ tracks, phases, topics: [topic('lost', 'PH99')], progress: [], complete: true }), /unplaced/)
  assert.throws(() => buildProgressJourney({ tracks, phases, topics: [], progress: [], complete: false }), /until all Topic pages have loaded/)
  assert.throws(() => buildProgressJourney({ tracks, phases, topics: [a], progress: [progress('a', 'Solid'), progress('a', 'Learning')], complete: true }), /Duplicate learner progress/)
})
