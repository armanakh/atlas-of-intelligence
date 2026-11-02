import { Link } from 'react-router-dom'

export function TopicLink({ id, title, detail }: { id: string; title?: string; detail?: string }) {
  const statusTone = detail === 'Solid' ? 'solid' : detail === 'In progress' ? 'pending' : detail === 'Unassessed' ? 'unassessed' : null
  return <Link className="topic-link" to={`/topics/${encodeURIComponent(id)}`}>
    <span className="topic-link__id">{id}</span><span className="topic-link__title">{title || id}</span>{detail && <span className={`topic-link__detail${statusTone ? ` topic-link__detail--${statusTone}` : ''}`}>{detail}</span>}<span className="topic-link__arrow" aria-hidden="true">↗</span>
  </Link>
}
