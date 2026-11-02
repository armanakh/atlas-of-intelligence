import { useMemo, useState } from 'react'
import { useAtlas, isNoActiveRelease } from '../../app/AtlasContext'
import { EmptyRelease, ErrorNote, LoadingLine } from '../../components/StateViews'
import { AtlasDataIncompleteError, buildAtlasSurveyModel, filterIdeas, resolveSurveyState, type AtlasSurveyModel } from './atlasModel'

function classes(base: string, modifier?: string, selected = false) {
  return [base, modifier, selected ? 'is-selected' : ''].filter(Boolean).join(' ')
}

function slug(id: string) {
  return id.toLowerCase().replace('tr-', '')
}

export function AtlasSurveyPage() {
  const atlas = useAtlas()
  const [territoryIds, setTerritoryIds] = useState<Set<string>>(() => new Set())
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null)
  const survey = useMemo<{ model: AtlasSurveyModel | null; error: Error | null }>(() => {
    if (!atlas.releaseId || atlas.isLoadingData || atlas.dataError || !atlas.hierarchy) return { model: null, error: null }
    try {
      return { model: buildAtlasSurveyModel({
        tracks: atlas.hierarchy.tracks.map(({ track }) => track),
        phases: atlas.hierarchy.phases.map(({ phase }) => phase),
        topics: atlas.topics,
        complete: true,
      }), error: null }
    } catch (error) {
      return { model: null, error: error instanceof Error ? error : new Error('The Topic data could not be surveyed.') }
    }
  }, [atlas.releaseId, atlas.isLoadingData, atlas.dataError, atlas.hierarchy, atlas.topics])

  if (!atlas.releaseId) {
    if (atlas.releaseLoading) return <div className="page-state"><LoadingLine label="Finding the active release…" /></div>
    if (isNoActiveRelease(atlas.releaseError)) return <EmptyRelease releases={atlas.releases} onSelect={(id) => void atlas.selectRelease(id)} pending={atlas.selectingRelease} />
    return <div className="page atlas-survey"><ErrorNote message={atlas.releaseError?.message || 'The release could not be loaded.'} /></div>
  }
  const loadState = resolveSurveyState({ loading: atlas.isLoadingData, error: atlas.dataError || survey.error, complete: survey.model?.complete === true, ideaCount: survey.model?.ideas.length || 0 })
  if (loadState === 'loading') return <div className="page-state"><LoadingLine label="Surveying every Topic in this release…" /></div>
  if (loadState === 'error') {
    const error = survey.error || atlas.dataError
    return <div className="page atlas-survey"><ErrorNote title={survey.error ? 'The release data is inconsistent' : 'The survey could not be completed'} message={error instanceof Error ? error.message : 'The local curriculum data could not be loaded.'} /></div>
  }
  const model = survey.model
  if (loadState === 'incomplete' || !model || model.complete !== true) return <div className="page atlas-survey"><ErrorNote title="The survey is incomplete" message={new AtlasDataIncompleteError().message} /></div>
  if (loadState === 'empty') return <div className="page atlas-survey"><div className="atlas-empty"><span>NO IDEAS IN THIS RELEASE</span><h1>An empty survey</h1><p>This release contains no Topics to map.</p></div></div>

  const selectedIdea = selectedIdeaId ? model.ideas.find((idea) => idea.id === selectedIdeaId) : undefined
  const selectedField = selectedIdea ? model.fields.find((field) => field.id === selectedIdea.phaseId) : undefined
  const totalTerritoryMemberships = model.territories.reduce((sum, territory) => sum + territory.ideaCount, 0)
  const filteredIdeaCount = model.fields.reduce((sum, field) => sum + filterIdeas(field.ideas, [...territoryIds]).length, 0)
  const toggleTerritory = (id: string) => setTerritoryIds((current) => {
    const next = new Set(current)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })
  const selectedTerritoryNames = model.territories.filter((item) => territoryIds.has(item.id)).map((item) => item.title)
  const progressByTopic = new Map(atlas.progress.map((record) => [record.topic_id, record]))
  const progressFor = (ideaId: string) => {
    if (!atlas.learnerId || atlas.progressError) return { label: 'Unavailable', tone: 'unavailable' }
    const record = progressByTopic.get(ideaId)
    const label = record?.progress_status || 'Unassessed'
    const tone = label.toLowerCase().replace(/\s+/g, '-')
    return { label, tone }
  }

  return <main className="page atlas-survey" aria-labelledby="atlas-survey-title">
    <div className="atlas-survey__eyebrow"><span>ATLAS OF INTELLIGENCE</span><span>CURRICULUM {atlas.release?.curriculum_version} · SURVEY</span></div>
    <header className="atlas-survey__hero">
      <div><p className="atlas-survey__kicker">Selected release · {atlas.release?.curriculum_version}</p><h1 id="atlas-survey-title">Ideas across<br /><em>Territories &amp; Fields.</em></h1></div>
      <p className="atlas-survey__intro">Explore {model.ideas.length} stable Ideas through {model.territories.length} overlapping Territory lenses and {model.fields.length} ordered Phase placements.</p>
    </header>
    <div className="atlas-survey__summary" aria-label="Loaded curriculum counts">
      <div><strong>{model.territories.length}</strong><span>Territories</span></div>
      <div><strong>{model.fields.length}</strong><span>Fields in source order</span></div>
      <div><strong>{model.ideas.length}</strong><span>unique Ideas</span></div>
      <div><strong>{totalTerritoryMemberships}</strong><span>Track affiliations · overlapping</span></div>
    </div>

    <section className="territory-lenses" aria-labelledby="territory-heading">
      <div className="atlas-section-heading"><div><span className="atlas-label">TRACK MEMBERSHIP · OVERLAPS PRESERVED</span><h2 id="territory-heading">Choose a Territory lens</h2></div><span className="atlas-microcopy">Color identifies membership</span></div>
      <div className="territory-lenses__list">
        <button className={classes('territory-lens', 'territory-lens--all', territoryIds.size === 0)} aria-pressed={territoryIds.size === 0} onClick={() => setTerritoryIds(new Set())}><span className="territory-lens__mark" aria-hidden="true">◎</span><span><strong>All Territories</strong><small>Show every affiliation</small></span><b>{model.ideas.length}</b></button>
        {model.territories.map((territory) => <button key={territory.id} className={classes('territory-lens', 'territory-lens--' + slug(territory.id), territoryIds.has(territory.id))} aria-pressed={territoryIds.has(territory.id)} onClick={() => toggleTerritory(territory.id)}>
          <span className="territory-lens__mark" aria-hidden="true">{territory.id === 'TR-MATH' ? '∴' : territory.id === 'TR-CS' ? '⌘' : territory.id === 'TR-ENG' ? '⌗' : territory.id === 'TR-ML' ? '≋' : '◎'}</span>
          <span><strong>{territory.title}</strong><small>{territory.description}</small><em>{territory.editorial ? 'Provisional description' : 'Source description'}</em></span><b>{territory.ideaCount}</b>
        </button>)}
      </div>
      <p className="atlas-editorial-note">Territory descriptions are provisional editorial metadata. Names and memberships come from the selected release.</p>
    </section>

    <section className="field-survey" aria-labelledby="field-heading">
      <div className="atlas-section-heading field-survey__heading"><div><span className="atlas-label">PHASE PLACEMENT · SOURCE ORDER</span><h2 id="field-heading">Seventeen Fields</h2><p>Ordered as published. Position does not determine readiness.</p></div>
        {territoryIds.size > 0 && <button className="atlas-reset" onClick={() => setTerritoryIds(new Set())}>Showing {selectedTerritoryNames.join(' + ')} · Clear ×</button>}
      </div>
      <div className="field-survey__bands">
        {territoryIds.size > 0 && filteredIdeaCount === 0 && <div className="atlas-filter-empty" role="status"><strong>No Ideas match these Territories.</strong><span>Clear a lens or select a different Territory to continue exploring.</span><button className="atlas-reset" onClick={() => setTerritoryIds(new Set())}>Show all Ideas</button></div>}
        {model.fields.map((field) => {
          const visibleIdeas = filterIdeas(field.ideas, [...territoryIds])
          return <details className="field-band" key={field.id}>
            <summary>
              <span className="field-band__ordinal">{String(field.ordinal).padStart(2, '0')}</span>
              <span className="field-band__identity"><small>{field.id}</small><strong>{field.title}</strong></span>
              <span className="field-band__count"><b>{field.ideaCount}</b><small>Ideas</small></span>
              <span className="field-band__intersections" aria-label="Territory memberships in this Field">
                {field.territoryIntersections.filter((intersection) => intersection.ideaCount > 0).map((intersection) => {
                  const territory = model.territories.find((item) => item.id === intersection.territoryId)!
                  return <span key={intersection.territoryId} className={classes('field-affiliation field-affiliation--' + slug(intersection.territoryId), undefined, territoryIds.has(intersection.territoryId))} title={territory.title + ': ' + intersection.ideaCount + ' Ideas'}><i aria-hidden="true" />{territory.title}<b>{intersection.ideaCount}</b></span>
                })}
              </span>
              <span className="field-band__toggle" aria-hidden="true">＋</span>
            </summary>
            <div className="field-band__ideas">
              <p>{territoryIds.size ? visibleIdeas.length + ' matching Ideas · ' + field.ideaCount + ' total in this Field' : field.ideaCount + ' Ideas · one Phase placement each'}</p>
              {visibleIdeas.map((idea) => <button key={idea.id} className={classes('survey-idea', undefined, selectedIdeaId === idea.id)} aria-pressed={selectedIdeaId === idea.id} onClick={() => setSelectedIdeaId(selectedIdeaId === idea.id ? null : idea.id)}>
                <code>{idea.id}</code><strong>{idea.title}</strong><span className="survey-idea__affiliations" aria-label="Territory affiliations">{idea.territoryIds.map((id) => <span key={id} className={'survey-idea__affiliation survey-idea__affiliation--' + slug(id)}>{model.territories.find((territory) => territory.id === id)?.title || id}</span>)}</span><span className={'idea-progress idea-progress--' + progressFor(idea.id).tone} aria-label={'Progress: ' + progressFor(idea.id).label}>{progressFor(idea.id).label}</span><span className="survey-idea__open">{selectedIdeaId === idea.id ? 'Selected' : 'Inspect'}</span>
              </button>)}
              {visibleIdeas.length === 0 && <p className="field-band__empty">No Ideas in this Field have that Territory membership.</p>}
            </div>
          </details>
        })}
      </div>
    </section>

    {model.unplacedIdeas.length > 0 && <aside className="atlas-data-note" role="status">{model.unplacedIdeas.length} Ideas have no valid Phase placement in this release. They remain identified but are not assigned to a Field.</aside>}

    {selectedIdea && <aside className="idea-inspector" aria-live="polite" aria-label="Selected Idea">
      <div><span className="atlas-label">SELECTED IDEA · {selectedIdea.id}</span><button className="idea-inspector__close" onClick={() => setSelectedIdeaId(null)} aria-label="Close selected Idea">×</button><h2>{selectedIdea.title}</h2><p>{selectedIdea.description || 'No description is available in this release.'}</p>
        <dl><div><dt>Field placement</dt><dd>{selectedField ? selectedField.id + ' · ' + selectedField.title : 'No Phase placement'}</dd></div><div><dt>Territory affiliations</dt><dd>{selectedIdea.territoryIds.length ? selectedIdea.territoryIds.map((id) => model.territories.find((territory) => territory.id === id)?.title || id).join(' · ') : 'No Track memberships'}</dd></div><div><dt>Learner status</dt><dd><span className={'idea-progress idea-progress--' + progressFor(selectedIdea.id).tone}>{progressFor(selectedIdea.id).label}</span></dd></div></dl>
      </div>
    </aside>}
    <footer className="atlas-survey__footer"><span>{model.ideas.length} unique Ideas · {model.unplacedIdeas.length} without a Field placement</span><span>No relationship lines are inferred from position.</span></footer>
  </main>
}
