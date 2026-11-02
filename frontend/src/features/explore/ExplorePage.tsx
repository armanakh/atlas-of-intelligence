import { useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAtlas } from '../../app/AtlasContext'
import { TopicLink } from '../../components/TopicLink'
import { LoadingLine } from '../../components/StateViews'
import { PROGRESS_STATUSES } from '../../api/types'

export function ExplorePage() {
  const atlas = useAtlas()
  const [params, setParams] = useSearchParams()
  const paramsRef = useRef(params)
  paramsRef.current = params
  const search = params.get('q') || ''
  const track = params.get('track') || ''
  const phase = params.get('phase') || ''
  const status = params.get('status') || ''
  const activeCriteria = [
    search.trim() ? `Search · “${search.trim()}”` : '',
    track ? `Territory · ${atlas.hierarchy?.tracks.find(({ track: item }) => item.id === track)?.track.title || track}` : '',
    phase ? `Field · ${phase} · ${atlas.hierarchy?.phases.find(({ phase: item }) => item.id === phase)?.phase.title || ''}` : '',
    status ? `Progress · ${status}` : '',
  ].filter(Boolean)
  const progressByTopic = useMemo(() => new Map(atlas.progress.map((row) => [row.topic_id, row])), [atlas.progress])
  const filtered = useMemo(() => atlas.topics.filter((topic) => {
    const normalized = search.trim().toLowerCase()
    const textMatch = !normalized || `${topic.id} ${topic.title} ${topic.description || ''}`.toLowerCase().includes(normalized)
    const trackMatch = !track || topic.track_ids.includes(track)
    const phaseMatch = !phase || topic.phase_id === phase
    const row = progressByTopic.get(topic.id)
    const statusMatch = !status || (status === 'Unassessed' ? !row : row?.progress_status === status)
    return textMatch && trackMatch && phaseMatch && statusMatch
  }), [atlas.topics, search, track, phase, status, progressByTopic])

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(paramsRef.current)
    value ? next.set(key, value) : next.delete(key)
    paramsRef.current = next
    setParams(next, { replace: true })
  }
  const clearFilters = () => {
    const next = new URLSearchParams()
    paramsRef.current = next
    setParams(next, { replace: true })
  }
  if (!atlas.releaseId) return <div className="page page--short"><div className="eyebrow">Field index</div><h1>Explore the map</h1><p className="page-intro">Choose an active curriculum release from the header to begin browsing.</p></div>
  if (atlas.isLoadingData) return <div className="page-state"><LoadingLine label="Indexing the Topics…" /></div>

  return <div className="page explore-page">
    <div className="page-kicker"><span>FIELD INDEX</span><span>CURRICULUM {atlas.release?.curriculum_version}</span></div>
    <div className="explore-heading"><div><div className="eyebrow">Find a concept, follow its edges</div><h1>Explore <em>the ideas.</em></h1></div><p>Search by name or stable Topic ID. Each filter narrows results; matching Ideas keep all their Territory affiliations visible.</p></div>
    <div className="explore-controls">
      <label className="search-field"><span aria-hidden="true">⌕</span><input aria-label="Search topics" value={search} onChange={(event) => update('q', event.target.value)} placeholder="Search the atlas…" /><kbd>/</kbd></label>
      <label className="filter-field"><span>TRACK</span><select value={track} onChange={(event) => update('track', event.target.value)}><option value="">All tracks</option>{atlas.hierarchy?.tracks.map(({ track: item }) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      <label className="filter-field"><span>PHASE</span><select value={phase} onChange={(event) => update('phase', event.target.value)}><option value="">All phases</option>{atlas.hierarchy?.phases.map(({ phase: item }) => <option key={item.id} value={item.id}>{item.id} · {item.title}</option>)}</select></label>
      <label className="filter-field"><span>PROGRESS</span><select value={status} onChange={(event) => update('status', event.target.value)}><option value="">Any state</option><option value="Unassessed">Unassessed</option>{PROGRESS_STATUSES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
    </div>
    <div className="results-line"><span><strong>{filtered.length}</strong> Topics found</span>{(search || track || phase || status) && <button className="text-button" onClick={clearFilters}>Clear filters ×</button>}<span className="results-note">Sorted by Topic ID</span></div>
    {activeCriteria.length > 0 && <div className="explore-active-filters" aria-live="polite"><span>Matching all:</span>{activeCriteria.map((criterion) => <b key={criterion}>{criterion}</b>)}<small>Other overlapping Territory affiliations remain shown on each Idea.</small></div>}
    <div className="topic-table" role="list">
      {filtered.map((topic, index) => {
        const progress = progressByTopic.get(topic.id)
        const trackLabels = topic.track_ids.map((id) => atlas.hierarchy?.tracks.find((row) => row.track.id === id)?.track.title || id)
        const phaseLabel = topic.phase_id ? atlas.hierarchy?.phases.find((row) => row.phase.id === topic.phase_id)?.phase.title : undefined
        return <article className="topic-table-row" role="listitem" key={topic.id}>
          <span className="topic-table-row__index">{String(index + 1).padStart(3, '0')}</span>
          <div className="topic-table-row__content"><TopicLink id={topic.id} title={topic.title} /><p>{topic.description || 'A concept in the curriculum map.'}</p><div className="topic-tags">{topic.track_ids.map((id, trackIndex) => <span className={`topic-tag topic-tag--track territory-tone--${id.toLowerCase().replace('tr-', '')}`} key={id} title={`Territory membership: ${trackLabels[trackIndex]}`}>{trackLabels[trackIndex]}</span>)}{phaseLabel && <span className="topic-tag topic-tag--phase">{phaseLabel}</span>}</div></div>
          <div className={`progress-stamp progress-stamp--${progress?.progress_status?.toLowerCase().replace(/\s+/g, '-') || 'unassessed'}`}><i />{progress?.progress_status || 'Unassessed'}</div>
          <span className="topic-table-row__confidence">{progress?.confidence ? `Confidence ${progress.confidence}/5` : ''}</span>
        </article>
      })}
      {!filtered.length && <div className="no-results"><span>∅</span><strong>No Topics match this view.</strong><p>Try a broader phrase or clear one of the filters.</p><button className="text-button" onClick={clearFilters}>Reset the index</button></div>}
    </div>
  </div>
}
