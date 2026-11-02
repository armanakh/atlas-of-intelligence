import { Link } from 'react-router-dom'
import { useAtlas, isNoActiveRelease } from '../../app/AtlasContext'
import { EmptyRelease } from '../../components/StateViews'

const trackColor = ['moss', 'ochre', 'blue', 'clay', 'plum']

export function RoadmapPage() {
  const atlas = useAtlas()
  if (!atlas.releaseId) {
    if (atlas.releaseLoading) return <div className="page-state">Opening the atlas…</div>
    if (isNoActiveRelease(atlas.releaseError)) return <EmptyRelease releases={atlas.releases} onSelect={(id) => void atlas.selectRelease(id)} pending={atlas.selectingRelease} />
    return <div className="page-state">The release could not be loaded. Check that the local API is running.</div>
  }
  if (!atlas.hierarchy || atlas.isLoadingData) return <div className="page-state">Reading the structure of this release…</div>

  const progressByTopic = new Map(atlas.progress.map((row) => [row.topic_id, row]))
  const learnerAvailable = Boolean(atlas.learnerId)
  const solidCount = learnerAvailable ? atlas.progress.filter((row) => row.progress_status === 'Solid').length : null
  const assessed = learnerAvailable ? atlas.progress.length : null
  const activeTracks = atlas.hierarchy.tracks
  const phases = atlas.hierarchy.phases
  const phaseTopicCounts = phases.reduce((sum, item) => sum + item.topic_ids.length, 0)
  return <div className="page roadmap-page">
    <div className="page-heading page-heading--roadmap">
      <div>
        <div className="eyebrow">A living map · Curriculum {atlas.release?.curriculum_version}</div>
        <h1>Knowledge has<br /><em>many ways in.</em></h1>
        <p className="page-intro">Follow a line of mathematics, move through computation, or begin wherever a question takes you.</p>
        <div className="heading-meta"><span className="release-status"><i />{atlas.release?.status?.replaceAll('_', ' ') || 'Curriculum release'}</span><span>{atlas.release?.schema_version}</span></div>
      </div>
      <div className="roadmap-illustration" aria-hidden="true">
        <svg viewBox="0 0 360 250" role="presentation">
          <defs><linearGradient id="routeFade" x1="0" x2="1"><stop stopColor="#b98043" /><stop offset="1" stopColor="#477d72" /></linearGradient></defs>
          <path d="M29 203C80 180 75 135 126 129s56 48 97 22 36-93 105-111" fill="none" stroke="url(#routeFade)" strokeWidth="1.5" />
          <path d="M17 180c49-31 69-50 112-48s58 39 88 26 53-75 103-94M40 225c47-17 53-62 104-69s57 54 91 35 39-73 91-89" fill="none" stroke="#70857e" strokeWidth=".7" opacity=".45" />
          <path d="M94 28c28 28 38 59 33 93M229 16c-4 42 11 67 38 83M192 165c16 21 16 43 3 67" fill="none" stroke="#b4aa94" strokeWidth=".65" strokeDasharray="2 6" />
          <circle cx="29" cy="203" r="4" fill="#b98043" /><circle cx="126" cy="129" r="4" fill="#547f71" /><circle cx="223" cy="151" r="4" fill="#647f9c" /><circle cx="328" cy="40" r="4" fill="#6d7064" />
          <circle cx="29" cy="203" r="11" fill="none" stroke="#b98043" strokeOpacity=".4" /><circle cx="223" cy="151" r="12" fill="none" stroke="#647f9c" strokeOpacity=".38" />
          <text x="19" y="232">ORIGIN</text><text x="111" y="111">STRUCTURE</text><text x="213" y="132">LEARNING</text><text x="298" y="21">INTELLIGENCE</text>
        </svg>
        <span className="map-caption">A route is a suggestion,<br />never a gate.</span>
      </div>
    </div>

    <div className="atlas-ribbon" aria-label="Curriculum summary">
      <div><span className="ribbon-number">{atlas.topics.length || atlas.releaseDetail?.topic_count || 0}</span><span className="ribbon-label">Topics in this edition</span></div>
      <div><span className="ribbon-number">{activeTracks.length}</span><span className="ribbon-label">Ways to traverse</span></div>
      <div><span className="ribbon-number">{phases.length}</span><span className="ribbon-label">Phases of study</span></div>
      <div><span className="ribbon-number">{assessed ?? '—'}<small> / {atlas.topics.length || atlas.releaseDetail?.topic_count || 0}</small></span><span className="ribbon-label">{learnerAvailable ? 'Topics assessed' : 'Learner assessment unavailable'}</span></div>
      <div className="ribbon-note">{learnerAvailable ? <>{solidCount} marked Solid<br /><span>Progress belongs to you.</span></> : <>Your personal record<br /><span>Could not be resolved.</span></>}</div>
    </div>

    <section className="atlas-section tracks-section">
      <div className="section-heading"><div><span className="section-index">01 / DIRECTIONS</span><h2>Choose a line of inquiry</h2></div><Link to="/topics" className="section-link">Browse all topics <span>↗</span></Link></div>
      <p className="section-deck">Tracks overlap by design. A Topic may belong to several; each perspective reveals a different shape.</p>
      <div className="track-list">
        {activeTracks.map(({ track, topic_ids }, index) => {
          const solid = learnerAvailable ? topic_ids.filter((id) => progressByTopic.get(id)?.progress_status === 'Solid').length : null
          return <Link to={`/topics?track=${encodeURIComponent(track.id)}`} className={`track-row track-row--${trackColor[index % trackColor.length]}`} key={track.id}>
            <span className="track-row__index">0{index + 1}</span>
            <span className="track-row__path" aria-hidden="true"><i /></span>
            <span className="track-row__main"><span className="track-row__title">{track.title}</span><span className="track-row__id">{track.id}</span></span>
            <span className="track-row__summary">{topic_ids.length} topics · {solid == null ? 'progress unavailable' : `${solid} Solid`}</span>
            <span className="track-row__arrow" aria-hidden="true">↗</span>
          </Link>
        })}
      </div>
    </section>

    <section className="atlas-section phase-section">
      <div className="section-heading"><div><span className="section-index">02 / PLACEMENT</span><h2>Phases, as a horizon</h2></div><span className="phase-total">{phaseTopicCounts} placements · Topics may take more than one route</span></div>
      <p className="section-deck">A useful map of the curriculum's broad movement, not a required sequence.</p>
      <div className="phase-rail">
        {phases.map(({ phase, topic_ids }, index) => {
          const studied = learnerAvailable ? topic_ids.filter((id) => progressByTopic.has(id)).length : null
          return <Link className="phase-stop" to={`/topics?phase=${encodeURIComponent(phase.id)}`} key={phase.id}>
            <span className="phase-stop__axis"><i /><b>{String(index).padStart(2, '0')}</b></span>
            <span className="phase-stop__copy"><span className="phase-stop__id">{phase.id}</span><strong>{phase.title}</strong><small>{topic_ids.length} topics <i>·</i> {studied == null ? 'assessment unavailable' : `${studied} assessed`}</small></span>
            <span className="phase-stop__arrow">↗</span>
          </Link>
        })}
      </div>
    </section>

    <section className="closing-note">
      <span className="closing-note__symbol">∞</span>
      <p>The map describes relationships. <em>Your curiosity chooses the route.</em></p>
      <Link to="/progress">Look at your progress <span>↗</span></Link>
    </section>
    <footer className="page-footer"><span>ATLAS OF INTELLIGENCE</span><span>LOCAL KNOWLEDGE · PRIVATE BY DESIGN</span></footer>
  </div>
}
