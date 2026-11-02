import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api } from '../../api/client'
import { useAtlas } from '../../app/AtlasContext'
import { TopicLink } from '../../components/TopicLink'
import { ProgressEditor } from '../../components/ProgressEditor'
import { LoadingLine } from '../../components/StateViews'

function readinessName(value: 'ready' | 'not_ready' | 'unknown') {
  return value === 'ready' ? 'Ready' : value === 'not_ready' ? 'Not ready' : 'Unknown'
}

export function TopicPage() {
  const { topicId = '' } = useParams()
  const atlas = useAtlas()
  const releaseId = atlas.releaseId
  const learnerId = atlas.learnerId
  const detail = useQuery({ queryKey: ['topic', releaseId, topicId], queryFn: () => api.topic(releaseId!, topicId), enabled: Boolean(releaseId && topicId) })
  const dependencies = useQuery({ queryKey: ['dependencies', releaseId, topicId], queryFn: () => api.dependencies(releaseId!, topicId), enabled: Boolean(releaseId && topicId) })
  const readiness = useQuery({ queryKey: ['readiness', releaseId, learnerId, topicId], queryFn: () => api.readiness(releaseId!, learnerId!, topicId), enabled: Boolean(releaseId && learnerId && topicId) })
  const progress = atlas.progress.find((row) => row.topic_id === topicId)
  const titleFor = (id: string) => atlas.topics.find((topic) => topic.id === id)?.title || id
  if (!releaseId) return <div className="page page--short"><Link className="back-link" to="/roadmap">← Return to the map</Link><h1>Choose a curriculum release</h1></div>
  if (detail.isLoading) return <div className="page-state"><LoadingLine label="Opening this Topic…" /></div>
  if (detail.error || !detail.data) {
    const error = detail.error as ApiError | null
    return <div className="page page--short"><Link className="back-link" to="/topics">← Back to Explore</Link><div className="not-found"><span>?</span><h1>This Topic is outside this release.</h1><p>{error?.message || 'The Topic could not be found.'}</p></div></div>
  }
  const topic = detail.data
  const groups = dependencies.data?.prerequisite_groups || topic.prerequisite_groups
  const metadataIds = ['learning_resource_ids', 'exercise_ids', 'project_ids'] as const
  const items = metadataIds.flatMap((key) => {
    const values = topic.metadata[key]
    return Array.isArray(values) ? values.map((value) => ({ kind: key.replace('_ids', '').replaceAll('_', ' '), id: String(value) })) : []
  })
  const learningTarget = typeof topic.metadata.learning_target === 'string' ? topic.metadata.learning_target : null
  const depthFrontier = Array.isArray(topic.metadata.depth_frontier) ? topic.metadata.depth_frontier.filter((item): item is string => typeof item === 'string') : []
  const revisitTriggers = Array.isArray(topic.metadata.revisit_triggers) ? topic.metadata.revisit_triggers.filter((item): item is string => typeof item === 'string') : []
  const phaseTitle = atlas.hierarchy?.phases.find(({ phase }) => phase.id === topic.phase_id)?.phase.title
  const trackTitles = topic.track_ids.map((id) => atlas.hierarchy?.tracks.find(({ track }) => track.id === id)?.track.title || id)
  const readinessView = readiness.data

  return <div className="page topic-page">
    <div className="topic-page__top"><Link className="back-link" to="/topics">← Field index</Link><span className="topic-top__release">CURRICULUM {atlas.release?.curriculum_version}</span></div>
    <header className="topic-hero">
      <div className="topic-hero__meta"><span className="topic-id-large">{topic.id}</span>{phaseTitle && <span className="topic-location">{topic.phase_id} · {phaseTitle}</span>}</div>
      <h1>{topic.title}</h1>
      <p className="topic-description">{topic.description || 'This Topic is part of the curriculum map. Its descriptive content has not yet been authored.'}</p>
      <div className="topic-tags topic-tags--hero">{trackTitles.map((track) => <span className="topic-tag topic-tag--track" key={track}>{track}</span>)}{topic.pathway && <span className="topic-tag topic-tag--pathway">{topic.pathway}</span>}</div>
    </header>

    <div className="topic-layout">
      <div className="topic-main-column">
        <section className="topic-section objectives-section"><div className="section-index">01 / INTENT</div><h2>What this Topic opens</h2>
          {learningTarget && <div className="learning-target"><span>LEARNING TARGET</span><p>{learningTarget}</p></div>}
          {topic.objectives.length ? <ul className="objective-list">{topic.objectives.map((objective, index) => <li key={`${index}-${objective.text}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{objective.text}</p></li>)}</ul> : <p className="quiet-empty">Learning objectives have not been authored for this Topic yet.</p>}
          {(depthFrontier.length > 0 || revisitTriggers.length > 0) && <div className="topic-guidance-grid">
            {depthFrontier.length > 0 && <div><span>BEYOND THIS PASS</span><ul>{depthFrontier.map((item) => <li key={item}>{item}</li>)}</ul></div>}
            {revisitTriggers.length > 0 && <div><span>RETURN WHEN</span><ul>{revisitTriggers.map((item) => <li key={item}>{item}</li>)}</ul></div>}
          </div>}
        </section>
        <section className="topic-section assessment-section"><div className="section-index">02 / YOUR READING</div><div className="section-title-row"><div><h2>Your assessment</h2><p>Record progress and confidence as separate judgments.</p></div>{progress && <span className="last-updated">Updated {new Date(progress.updated_at).toLocaleDateString()}</span>}</div><ProgressEditor topicId={topic.id} progress={progress} /></section>
        <section className="topic-section relationships-section"><div className="section-index">03 / WHAT FOLLOWS</div><h2>Downstream dependencies</h2><p className="section-blurb">Topics that name this one as a prerequisite. Explore them in any order.</p>
          {dependencies.isLoading ? <LoadingLine label="Following downstream links…" /> : dependencies.data?.downstream_dependent_ids.length ? <div className="related-list">{dependencies.data.downstream_dependent_ids.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} detail="Depends on this Topic" />)}</div> : <p className="quiet-empty">No downstream Topics are registered in this release.</p>}
        </section>
      </div>
      <aside className="topic-side-column">
        <section className={`readiness-card readiness-card--${readinessView?.readiness || 'unknown'}`}>
          <div className="readiness-card__header"><span className="section-index">READINESS</span>{readinessView ? <strong>{readinessName(readinessView.readiness)}</strong> : <strong>Informational</strong>}</div>
          <p>{readinessView?.readiness === 'ready' ? 'At least one complete prerequisite path is Solid.' : readinessView?.readiness === 'not_ready' ? 'No complete prerequisite group is currently Solid.' : readinessView?.readiness === 'unknown' ? 'Some prerequisite progress has not been assessed.' : 'Readiness describes prerequisite progress. It never limits what you can explore.'}</p>
          {readiness.isLoading && <LoadingLine label="Checking prerequisite progress…" />}
          {readinessView?.groups.length ? <div className="readiness-groups">{readinessView.groups.map((group, index) => <div className="readiness-group" key={group.group_ordinal}><span className="group-label">PATH {String(index + 1).padStart(2, '0')} · AND</span><div className="group-members">{group.satisfied_topic_ids.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} detail="Solid" />)}{group.not_satisfied_topic_ids.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} detail="In progress" />)}{group.unknown_topic_ids.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} detail="Unassessed" />)}</div>{index < readinessView.groups.length - 1 && <div className="or-divider"><i />OR<i /></div>}</div>)}</div> : groups.length ? <div className="prerequisite-groups">{groups.map((group, index) => <div className="prerequisite-group" key={group.group_ordinal}><span className="group-label">GROUP {String(index + 1).padStart(2, '0')} · AND</span>{group.requires_all.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} />)}{index < groups.length - 1 && <div className="or-divider"><i />OR<i /></div>}</div>)}</div> : <div className="no-prerequisites"><span>0</span><p>No formal prerequisites. Begin here, or follow another thread.</p></div>}
        </section>
        <section className="side-relationship side-relationship--related"><div className="section-index">RELATED IDEAS</div><h3>Alongside this</h3><p>Connected concepts, separate from prerequisite logic.</p>
          {topic.related_topic_ids.length ? <div className="related-list">{topic.related_topic_ids.map((id) => <TopicLink key={id} id={id} title={titleFor(id)} detail="Related" />)}</div> : <p className="quiet-empty">No related Topics are registered.</p>}
        </section>
        <section className="learning-items"><div className="section-index">LEARNING MATERIAL</div><h3>Resources & practice</h3>{items.length ? <div className="learning-item-list">{items.map((item) => <div key={`${item.kind}-${item.id}`}><span>{item.kind}</span><strong>{item.id}</strong></div>)}</div> : <p>No learning items are attached yet.</p>}</section>
      </aside>
    </div>
    <footer className="page-footer"><span>{topic.registry_status || 'CURRICULUM TOPIC'}</span><span>THE MAP IS A GUIDE, NOT A GATE</span></footer>
  </div>
}
