import assert from 'node:assert/strict'
import test from 'node:test'
import { buildAtlasSurveyModel, filterIdeas, resolveSurveyState } from '../src/features/atlas/atlasModel.ts'
import { collectAllPages } from '../src/api/pagination.ts'
import type { Phase, TopicSummary, Track } from '../src/api/types.ts'

const tracks: Track[] = [
  { id: 'TR-CS', title: 'Computer Science', metadata: {} },
  { id: 'TR-MATH', title: 'Mathematics', metadata: {} },
]
const phases: Phase[] = [
  { id: 'PH00', title: 'Foundations', metadata: {} },
  { id: 'PH01', title: 'Computation', metadata: {} },
]
function topic(id: string, phaseId: string | null, trackIds: string[]): TopicSummary {
  return { id, title: id + ' title', description: null, phase_id: phaseId, track_ids: trackIds, current_priority: null, metadata: {} }
}
function build(topics: TopicSummary[]) {
  return buildAtlasSurveyModel({ tracks, phases, topics, complete: true })
}

test('each Topic has one canonical Idea identity across its memberships', () => {
  const model = build([topic('CS-001', 'PH00', ['TR-CS', 'TR-MATH'])])
  assert.equal(model.ideas.length, 1)
  assert.equal(model.fields[0].ideas.length, 1)
  assert.strictEqual(model.fields[0].ideas[0], model.ideas[0])
  assert.deepEqual(model.ideas[0].territoryIds, ['TR-CS', 'TR-MATH'])
  assert.deepEqual(filterIdeas(model.ideas, 'TR-CS').map((idea) => idea.id), ['CS-001'])
})

test('duplicate stable Topic IDs are rejected rather than duplicated', () => {
  assert.throws(() => build([topic('CS-001', 'PH00', ['TR-CS']), topic('CS-001', 'PH01', ['TR-MATH'])]), /Duplicate Topic identity/)
})

test('a Topic has one Phase placement and absent placements are reported without assignment', () => {
  const model = build([topic('CS-001', 'PH01', ['TR-CS']), topic('NO-PHASE', null, ['TR-MATH'])])
  assert.equal(model.ideas[0].phaseId, 'PH01')
  assert.equal(model.unplacedIdeas[0].id, 'NO-PHASE')
  assert.deepEqual(model.fields.map((field) => field.id), ['PH00', 'PH01'])
  assert.equal(model.fields[0].ideaCount, 0)
  assert.equal(model.fields[1].ideaCount, 1)
})

test('Field intersections and Territory counts derive from membership rows', () => {
  const model = build([
    topic('A', 'PH00', ['TR-CS', 'TR-MATH']),
    topic('B', 'PH00', ['TR-CS']),
    topic('C', 'PH01', ['TR-MATH']),
  ])
  assert.deepEqual(model.fields[0].territoryIntersections, [
    { territoryId: 'TR-CS', ideaCount: 2 },
    { territoryId: 'TR-MATH', ideaCount: 1 },
  ])
  assert.deepEqual(model.territories.map(({ id, ideaCount }) => [id, ideaCount]), [['TR-CS', 2], ['TR-MATH', 2]])
  assert.equal(model.fields.reduce((sum, field) => sum + field.ideaCount, 0), 3)
})

test('filtering keeps one Idea even when it has multiple Territory affiliations', () => {
  const model = build([topic('CROSS', 'PH00', ['TR-CS', 'TR-MATH'])])
  const filtered = filterIdeas(model.fields[0].ideas, 'TR-MATH')
  assert.equal(filtered.length, 1)
  assert.equal(new Set(filtered.map((idea) => idea.id)).size, filtered.length)
  assert.deepEqual(filterIdeas(model.ideas, null).map((idea) => idea.id), ['CROSS'])
})

test('multi-Territory lenses use union membership without duplicating overlapping Ideas', () => {
  const model = build([
    topic('BOTH', 'PH00', ['TR-CS', 'TR-MATH']),
    topic('CS', 'PH00', ['TR-CS']),
    topic('MATH', 'PH01', ['TR-MATH']),
  ])
  const filtered = filterIdeas(model.ideas, ['TR-CS', 'TR-MATH'])
  assert.deepEqual(filtered.map((idea) => idea.id), ['BOTH', 'CS', 'MATH'])
  assert.equal(new Set(filtered.map((idea) => idea.id)).size, 3)
  assert.deepEqual(filterIdeas(model.ideas, []).map((idea) => idea.id), ['BOTH', 'CS', 'MATH'])
})

test('aggregates refuse incomplete Topic pages', () => {
  assert.throws(() => buildAtlasSurveyModel({ tracks, phases, topics: [topic('A', 'PH00', ['TR-CS'])], complete: false }), /all Topic pages have loaded/)
  assert.equal(resolveSurveyState({ loading: false, error: null, complete: false, ideaCount: 1 }), 'incomplete')
})

test('cursor collection waits through every page and rejects repeated cursors', async () => {
  const cursors: (string | null)[] = []
  const items = await collectAllPages(async (cursor) => {
    cursors.push(cursor)
    if (cursor === null) return { items: [1, 2], next_cursor: 'page-2' }
    return { items: [3], next_cursor: null }
  })
  assert.deepEqual(cursors, [null, 'page-2'])
  assert.deepEqual(items, [1, 2, 3])
  await assert.rejects(collectAllPages(async (cursor) => ({ items: [1], next_cursor: cursor === null ? 'loop' : 'loop' })), /repeated cursor/)
})

test('empty and error results remain distinct from loading and incomplete states', () => {
  assert.equal(resolveSurveyState({ loading: true, error: null, complete: false, ideaCount: 0 }), 'loading')
  assert.equal(resolveSurveyState({ loading: false, error: new Error('offline'), complete: false, ideaCount: 0 }), 'error')
  assert.equal(resolveSurveyState({ loading: false, error: null, complete: true, ideaCount: 0 }), 'empty')
  assert.equal(resolveSurveyState({ loading: false, error: null, complete: true, ideaCount: 2 }), 'ready')
})
