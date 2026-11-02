import { Link } from 'react-router-dom'
import { useMemo } from 'react'
import { useAtlas, isNoActiveRelease } from '../../app/AtlasContext'
import { EmptyRelease, LoadingLine } from '../../components/StateViews'
import {
  JOURNEY_STATUSES,
  buildProgressJourney,
  progressPercent,
  type JourneyField,
  type JourneyStatus,
  type StatusCounts,
} from './progressModel'

function tone(status: JourneyStatus) {
  return status.toLowerCase().replace(/\s+/g, '-')
}

function StatusBar({ counts, total, label }: { counts: StatusCounts; total: number; label: string }) {
  return <div className="journey-status-bar" role="img" aria-label={`${label}: ${JOURNEY_STATUSES.map((status) => `${counts[status]} ${status}`).join(', ')}`}>
    {JOURNEY_STATUSES.map((status) => counts[status] > 0 && <span key={status} className={`journey-status-bar__segment journey-status-bar__segment--${tone(status)}`} style={{ flexGrow: counts[status], flexBasis: 0 }} title={`${counts[status]} ${status} · ${progressPercent(counts[status], total)}`} />)}
  </div>
}

function StatusLegend({ counts, total }: { counts: StatusCounts; total: number }) {
  return <div className="journey-status-legend" aria-label="Idea progress summary">
    {JOURNEY_STATUSES.map((status) => <div className={`journey-status-legend__item journey-status-legend__item--${tone(status)}`} key={status}>
      <i aria-hidden="true" /><span>{status}</span><strong>{counts[status]}</strong><small>{progressPercent(counts[status], total)}</small>
    </div>)}
  </div>
}

function FieldStop({ field, territoryTitles }: { field: JourneyField; territoryTitles: ReadonlyMap<string, string> }) {
  const titleForTerritory = (id: string) => territoryTitles.get(id) || id
  return <details className="journey-field" id={`field-${field.id}`}>
    <summary className="journey-field__summary">
      <span className="journey-field__node"><i aria-hidden="true" /><b>{String(field.ordinal).padStart(2, '0')}</b></span>
      <span className="journey-field__identity"><small>{field.id} · FIELD</small><strong>{field.title}</strong><em>{field.ideaCount} Ideas · {field.assessedCount} assessed · {field.unassessedCount} unassessed</em></span>
      <span className="journey-field__coverage"><b>{progressPercent(field.counts.Solid, field.ideaCount)}</b><small>Solid share</small></span>
      <span className="journey-field__distribution"><StatusBar counts={field.counts} total={field.ideaCount} label={`${field.id} progress`} /><span>{field.counts.Solid} Solid · {field.counts.Learning} Learning · {field.counts.Practicing} Practicing · {field.counts.Revisit} Revisit · {field.counts['Not started']} Not started · {field.counts.Unassessed} Unassessed</span></span>
      <span className="journey-field__expand" aria-hidden="true">＋</span>
    </summary>
    <div className="journey-field__detail">
      <div className="journey-field__detail-head"><div><span className="journey-eyebrow">TERRITORY INTERSECTIONS</span><p>Track membership is shown independently from learning progress.</p></div>
        <div className="journey-field__territories">{field.territoryIntersections.filter(({ ideaCount }) => ideaCount > 0).map(({ territoryId, ideaCount }) => <span key={territoryId} className={`journey-territory territory-tone--${territoryId.toLowerCase().replace(/^tr-/, '')}`}><i aria-hidden="true" />{titleForTerritory(territoryId)} <b>{ideaCount}</b></span>)}</div>
      </div>
      <ul className="journey-ideas" aria-label={`Ideas in ${field.title}`}>
        {field.ideas.map((idea) => <li className="journey-idea" key={idea.id}>
          <span className="journey-idea__identity"><code>{idea.id}</code><Link to={`/topics/${encodeURIComponent(idea.id)}`}>{idea.title}</Link>{idea.description && <small>{idea.description}</small>}</span>
          <span className="journey-idea__territories" aria-label="Territory affiliations">{idea.territoryIds.map((id) => <span className={`journey-territory territory-tone--${id.toLowerCase().replace(/^tr-/, '')}`} key={id} title={titleForTerritory(id)}><i aria-hidden="true" />{titleForTerritory(id)}</span>)}</span>
          <span className={`journey-idea__status journey-idea__status--${tone(idea.progressStatus)}`}><i aria-hidden="true" />{idea.progressStatus}{idea.progressStatus === 'Unassessed' && !idea.hasProgressRecord && <small>No record</small>}</span>
          {idea.confidence != null && <span className="journey-idea__confidence">Confidence {idea.confidence}/5</span>}
        </li>)}
      </ul>
    </div>
  </details>
}

export function ProgressPage() {
  const atlas = useAtlas()
  const journey = useMemo(() => {
    if (!atlas.learnerId || atlas.progressError || atlas.dataError || !atlas.hierarchy) return null
    try {
      return buildProgressJourney({
        tracks: atlas.hierarchy.tracks.map(({ track }) => track),
        phases: atlas.hierarchy.phases.map(({ phase }) => phase),
        topics: atlas.topics,
        progress: atlas.progress,
        complete: true,
      })
    } catch (error) {
      return { error: error instanceof Error ? error : new Error('The Progress journey could not be derived.') }
    }
  }, [atlas.learnerId, atlas.progressError, atlas.dataError, atlas.hierarchy, atlas.topics, atlas.progress])

  if (!atlas.releaseId) {
    if (isNoActiveRelease(atlas.releaseError)) return <EmptyRelease releases={atlas.releases} onSelect={(id) => void atlas.selectRelease(id)} pending={atlas.selectingRelease} />
    if (atlas.releaseLoading) return <div className="page-state"><LoadingLine label="Finding the active release…" /></div>
    return <div className="page-state" role="alert">{atlas.releaseError?.message || 'The active curriculum release could not be loaded.'}</div>
  }
  if (atlas.learnerLoading || atlas.isLoadingData) return <div className="page-state"><LoadingLine label="Tracing your journey through the Fields…" /></div>

  if (!atlas.learnerId) return <main className="page progress-page progress-page--journey">
    <ProgressMasthead curriculumVersion={atlas.release?.curriculum_version} />
    <div className="journey-unavailable" role="alert"><span className="journey-eyebrow">LEARNER RECORD UNAVAILABLE</span><h1>The journey is here.<br /><em>Your record is not.</em></h1><p>{atlas.learnerError?.message || 'The local learner could not be resolved.'} No Ideas have been marked Unassessed by inference; without a resolved learner, no learner states are displayed.</p><Link to="/topics">Explore the curriculum <span aria-hidden="true">↗</span></Link></div>
  </main>

  if (atlas.progressError) return <main className="page progress-page progress-page--journey">
    <ProgressMasthead curriculumVersion={atlas.release?.curriculum_version} />
    <div className="journey-unavailable" role="alert"><span className="journey-eyebrow">LOCAL DATA COULD NOT BE READ</span><h1>Your learning record<br /><em>is temporarily unavailable.</em></h1><p>{atlas.progressError instanceof Error ? atlas.progressError.message : 'The learner progress response failed. Counts remain hidden until it can be loaded.'}</p><button className="journey-retry" onClick={atlas.refreshProgress}>Retry progress query</button></div>
  </main>

  if (atlas.dataError) return <main className="page progress-page progress-page--journey">
    <ProgressMasthead curriculumVersion={atlas.release?.curriculum_version} />
    <div className="journey-unavailable" role="alert"><span className="journey-eyebrow">CURRICULUM DATA COULD NOT BE READ</span><h1>The journey map<br /><em>is incomplete.</em></h1><p>{atlas.dataError instanceof Error ? atlas.dataError.message : 'The selected release data could not be loaded completely.'}</p></div>
  </main>

  if (!journey || 'error' in journey) return <main className="page progress-page progress-page--journey">
    <ProgressMasthead curriculumVersion={atlas.release?.curriculum_version} />
    <div className="journey-unavailable" role="alert"><span className="journey-eyebrow">RELEASE STRUCTURE NEEDS REVIEW</span><h1>This journey could not<br /><em>be placed faithfully.</em></h1><p>{journey && 'error' in journey ? journey.error.message : 'The release has no hierarchy data.'} No Field order or prerequisite relationships were inferred.</p></div>
  </main>

  const territoryTitles = new Map(atlas.hierarchy!.tracks.map(({ track }) => [track.id, track.title]))

  return <main className="page progress-page progress-page--journey" aria-labelledby="journey-title">
    <ProgressMasthead curriculumVersion={atlas.release?.curriculum_version} />
    <header className="journey-hero">
      <div className="journey-hero__copy"><span className="journey-eyebrow">YOUR LEARNING JOURNEY · {journey.chapters.length} CHAPTERS · {journey.fields.length} FIELDS</span><h1 id="journey-title">A path through<br /><em>the Ideas.</em></h1><p>The ordered Fields mark the landscape. Explore each stop in your own way; position gives the journey shape, not a prerequisite or a gate.</p></div>
      <div className="journey-hero__summary"><span className="journey-eyebrow">V3 CURRICULUM RELEASE</span><strong>{journey.ideaCount}</strong><span>unique Ideas across the journey</span><div className="journey-hero__summary-rule" /><b>{journey.assessedCount} assessed <i>·</i> {journey.unassessedCount} unassessed</b><small>Assessment status is separate from Territory affiliation.</small></div>
    </header>

    <section className="journey-overview" aria-labelledby="journey-overview-title">
      <div className="journey-section-heading"><div><span className="journey-eyebrow">THE WHOLE LANDSCAPE</span><h2 id="journey-overview-title">One journey, many states</h2></div><p>Overall, {progressPercent(journey.counts.Solid, journey.ideaCount)} of all Ideas are currently marked Solid. Each Field shows Solid Ideas divided by Ideas in that Field. These are self-assessment shares, not mastery scores.</p></div>
      <div className="journey-overview__bar"><StatusBar counts={journey.counts} total={journey.ideaCount} label="Overall journey" /></div>
      <StatusLegend counts={journey.counts} total={journey.ideaCount} />
      {journey.confidenceOnlyCount > 0 && <p className="journey-overview__note">{journey.confidenceOnlyCount} Ideas have a confidence value but no progress status; they remain Unassessed in this journey.</p>}
      <div className="journey-route-index" aria-label="Field stops in source order">
        {journey.fields.map((field) => <a key={field.id} href={`#field-${field.id}`} aria-label={`Jump to ${field.id}, ${field.title}. ${progressPercent(field.counts.Solid, field.ideaCount)} Solid share.`} title={`${field.id} · ${field.title} · ${progressPercent(field.counts.Solid, field.ideaCount)} Solid share`}>
          <span>{String(field.ordinal).padStart(2, '0')}</span><i><b style={{ height: `${field.solidShare * 100}%` }} /></i>
        </a>)}
      </div>
      <div className="journey-route-index__axis"><span>FOUNDATIONS</span><span>ADVANCED INTELLIGENCE</span></div>
      <div className="journey-route-index__key"><span><i aria-hidden="true" />Green fill shows the share of Ideas in each Field marked Solid.</span><span>Select a Field number to jump to its Ideas below.</span></div>
    </section>

    <section className="journey-chapters" aria-label="Curriculum journey chapters">
      {journey.chapters.map((chapter) => <article className={`journey-chapter journey-chapter--${chapter.id}`} id={`chapter-${chapter.id}`} key={chapter.id}>
        <header className="journey-chapter__header">
          <span className="journey-chapter__number">{chapter.number}</span>
          <div className="journey-chapter__heading"><span className="journey-eyebrow">CHAPTER {chapter.number} · {chapter.fields.length} FIELD STOPS</span><h2>{chapter.title}</h2><p>{chapter.purpose}</p></div>
          <div className="journey-chapter__summary"><strong>{chapter.ideaCount}</strong><span>Ideas</span><small>{chapter.counts.Solid} Solid · {chapter.unassessedCount} unassessed</small></div>
        </header>
        <div className="journey-chapter__progress"><StatusBar counts={chapter.counts} total={chapter.ideaCount} label={`${chapter.title} chapter`} /></div>
        <div className="journey-fields">
          {chapter.fields.map((field) => <FieldStop key={field.id} field={field} territoryTitles={territoryTitles} />)}
        </div>
      </article>)}
    </section>

    <footer className="journey-footer"><span>{journey.fields.length} ordered Fields · {journey.ideaCount} unique Ideas · {journey.progressRecordCount} learner progress records</span><span>Territories describe affiliation. Progress describes your current assessment.</span></footer>
  </main>
}

function ProgressMasthead({ curriculumVersion }: { curriculumVersion?: string }) {
  return <div className="journey-masthead"><span>ATLAS OF INTELLIGENCE</span><span>CURRICULUM {curriculumVersion || '—'} · PROGRESS</span></div>
}
