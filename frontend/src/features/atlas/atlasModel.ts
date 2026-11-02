import type { Phase, TopicSummary, Track } from '../../api/types'

export type TerritoryDefinition = {
  description: string
  editorial: true
}

// Provisional display copy from ATLAS_PRODUCT_ARCHITECTURE.md; Track IDs remain authoritative.
export const TERRITORY_PRESENTATION: Readonly<Record<string, TerritoryDefinition>> = {
  'TR-CS': { description: 'Programming, software design, data structures and algorithms as general computational practice.', editorial: true },
  'TR-MATH': { description: 'Formal and quantitative ideas for describing, deriving and reasoning about systems.', editorial: true },
  'TR-ENG': { description: 'Numerical implementation, inference and operational concerns around ML systems.', editorial: true },
  'TR-ML': { description: 'Learning methods, models, neural systems and applied ML techniques.', editorial: true },
  'TR-AI': { description: 'Ideas and systems concerned with intelligence and advanced AI.', editorial: true },
}

export type AtlasIdea = {
  id: string
  title: string
  description: string | null
  phaseId: string | null
  territoryIds: readonly string[]
}

export type TerritoryIntersection = {
  territoryId: string
  ideaCount: number
}

export type AtlasField = {
  id: string
  title: string
  ordinal: number
  ideaCount: number
  territoryIntersections: readonly TerritoryIntersection[]
  ideas: readonly AtlasIdea[]
}

export type AtlasTerritory = {
  id: string
  title: string
  description: string
  editorial: boolean
  ideaCount: number
}

export type AtlasSurveyModel = {
  complete: true
  territories: readonly AtlasTerritory[]
  fields: readonly AtlasField[]
  ideas: readonly AtlasIdea[]
  unplacedIdeas: readonly AtlasIdea[]
}

export class AtlasDataIncompleteError extends Error {
  constructor() {
    super('Atlas totals are unavailable until all Topic pages have loaded.')
    this.name = 'AtlasDataIncompleteError'
  }
}

export type AtlasSurveySource = {
  tracks: readonly Track[]
  phases: readonly Phase[]
  topics: readonly TopicSummary[]
  complete: boolean
}

export type SurveyLoadState = 'loading' | 'error' | 'incomplete' | 'empty' | 'ready'

export function resolveSurveyState(input: { loading: boolean; error: unknown; complete: boolean; ideaCount: number }): SurveyLoadState {
  if (input.loading) return 'loading'
  if (input.error) return 'error'
  if (!input.complete) return 'incomplete'
  if (input.ideaCount === 0) return 'empty'
  return 'ready'
}

/** Builds a release-scoped, read-only view model. Phase array order is preserved from the API. */
export function buildAtlasSurveyModel(source: AtlasSurveySource): AtlasSurveyModel {
  if (!source.complete) throw new AtlasDataIncompleteError()

  const ideaById = new Map<string, AtlasIdea>()
  for (const topic of source.topics) {
    if (ideaById.has(topic.id)) throw new Error(`Duplicate Topic identity in release: ${topic.id}`)
    ideaById.set(topic.id, {
      id: topic.id,
      title: topic.title,
      description: topic.description,
      phaseId: topic.phase_id,
      territoryIds: [...new Set(topic.track_ids)],
    })
  }

  const ideas = [...ideaById.values()]
  const trackById = new Map(source.tracks.map((track) => [track.id, track]))
  const territories: AtlasTerritory[] = source.tracks.map((track) => ({
    id: track.id,
    title: track.title,
    description: TERRITORY_PRESENTATION[track.id]?.description ?? 'Editorial description pending review.',
    editorial: TERRITORY_PRESENTATION[track.id]?.editorial ?? true,
    ideaCount: ideas.filter((idea) => idea.territoryIds.includes(track.id)).length,
  }))

  const phases = new Set(source.phases.map((phase) => phase.id))
  const unplacedIdeas = ideas.filter((idea) => !idea.phaseId || !phases.has(idea.phaseId))
  const fields: AtlasField[] = source.phases.map((phase, ordinal) => {
    const fieldIdeas = ideas.filter((idea) => idea.phaseId === phase.id)
    return {
      id: phase.id,
      title: phase.title,
      ordinal,
      ideaCount: fieldIdeas.length,
      territoryIntersections: territories.map((territory) => ({
        territoryId: territory.id,
        ideaCount: fieldIdeas.filter((idea) => idea.territoryIds.includes(territory.id)).length,
      })),
      ideas: fieldIdeas,
    }
  })

  // Preserve affiliations even if a future release adds a Track unknown to the current editorial config.
  for (const idea of ideas) {
    for (const territoryId of idea.territoryIds) {
      if (!trackById.has(territoryId)) {
        throw new Error(`Topic ${idea.id} references unknown Track ${territoryId}`)
      }
    }
  }

  return { complete: true, territories, fields, ideas, unplacedIdeas }
}

/** Filter canonical Idea objects; membership never expands one Idea into duplicate results. */
export function filterIdeas(ideas: readonly AtlasIdea[], territoryIds: string | readonly string[] | null): AtlasIdea[] {
  if (!territoryIds || (Array.isArray(territoryIds) && territoryIds.length === 0)) return [...ideas]
  const selected = new Set(typeof territoryIds === 'string' ? [territoryIds] : territoryIds)
  // Union semantics: show an Idea if it belongs to any selected Territory.
  // The input list is canonical, so overlapping memberships never duplicate Ideas.
  return ideas.filter((idea) => idea.territoryIds.some((id) => selected.has(id)))
}
