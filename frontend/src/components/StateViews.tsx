import { Link } from 'react-router-dom'

export function LoadingLine({ label = 'Tracing the curriculum…' }: { label?: string }) {
  return <div className="loading-line" role="status"><span className="loading-pip" />{label}</div>
}

export function ErrorNote({ title = 'The atlas could not be reached', message, onRetry }: { title?: string; message: string; onRetry?: () => void }) {
  return <div className="state-note state-note--error" role="alert"><span className="state-note__eyebrow">Local connection</span><strong>{title}</strong><p>{message}</p>{onRetry && <button className="text-button" onClick={onRetry}>Try again <span aria-hidden="true">↗</span></button>}</div>
}

export function EmptyRelease({ releases, onSelect, pending }: { releases: { release_id: string; curriculum_version: string; status: string | null }[]; onSelect: (id: string) => void; pending: boolean }) {
  return <section className="empty-release">
    <div className="empty-release__ornament" aria-hidden="true"><span>01</span><i /><span>∞</span></div>
    <div className="eyebrow">A map begins with a version</div>
    <h1>Choose the body of knowledge<br />you want to explore.</h1>
    <p>The imported curriculum is available as a release candidate. Select it explicitly to open its Tracks, Phases and Topics.</p>
    <div className="release-options">
      {releases.length ? releases.map((release) => <button key={release.release_id} className="release-option" disabled={pending} onClick={() => onSelect(release.release_id)}>
        <span className="release-option__index">↗</span><span><strong>Curriculum {release.curriculum_version}</strong><small>{release.status || 'Release'} · select to open</small></span><span className="release-option__arrow">→</span>
      </button>) : <p className="muted">No curriculum releases are available yet.</p>}
    </div>
    {pending && <LoadingLine label="Opening release…" />}
    <Link className="quiet-link" to="/progress">Your progress remains local and unchanged <span>↗</span></Link>
  </section>
}
