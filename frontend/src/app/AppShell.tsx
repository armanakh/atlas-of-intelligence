import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAtlas, isLearnerAmbiguous, isNoActiveRelease } from './AtlasContext'
import { AtlasMark } from '../components/AtlasMark'

const nav = [
  { to: '/roadmap', label: 'Home', symbol: '⌘', index: '01' },
  { to: '/topics', label: 'Explore', symbol: '⌕', index: '02' },
  { to: '/progress', label: 'Progress', symbol: '◷', index: '03' },
]

function routeTitle(path: string) {
  if (path.startsWith('/topics/')) return 'Topic field notes'
  if (path.startsWith('/topics')) return 'Field index'
  if (path.startsWith('/progress')) return 'Personal record'
  return 'Home · Atlas survey'
}

export function AppShell() {
  const atlas = useAtlas()
  const location = useLocation()
  const usesAtlasPalette = location.pathname === '/roadmap' || location.pathname.startsWith('/topics') || location.pathname.startsWith('/progress')
  const connectionError = atlas.releaseError?.status === 0 || atlas.learnerError?.status === 0
  const chooseRelease = (releaseId: string) => { if (releaseId) void atlas.selectRelease(releaseId) }

  return <div className={`app-shell${usesAtlasPalette ? ' app-shell--atlas' : ''}`}>
    <aside className="sidebar">
      <NavLink to="/roadmap" className="brand-lockup" aria-label="Atlas of Intelligence home"><AtlasMark /><span><b>ATLAS</b><small>OF INTELLIGENCE</small></span></NavLink>
      <div className="sidebar-rule"><span>PERSONAL KNOWLEDGE MAP</span></div>
      <nav className="primary-nav" aria-label="Primary navigation">
        {nav.map((item) => <NavLink to={item.to} key={item.to} className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}>
          <span className="nav-item__symbol" aria-hidden="true">{item.symbol}</span><span className="nav-item__label">{item.label}</span><span className="nav-item__index">{item.index}</span>
        </NavLink>)}
      </nav>
      <div className="sidebar-lower">
        <div className="sidebar-orbit" aria-hidden="true"><span /><i /><b /></div>
        <p>Mathematics<br />→ computation<br />→ intelligence</p>
        <span className="sidebar-edition">LOCAL EDITION · 01</span>
      </div>
      <div className="sidebar-footer"><span className="privacy-dot" />Your map stays on this device</div>
    </aside>

    <main className="workspace">
      <header className="topbar">
        <div className="topbar__context"><span className="topbar__context-label">{routeTitle(location.pathname)}</span><span className="topbar__separator">/</span><span className="topbar__context-sub">An atlas for the curious</span></div>
        <div className="topbar__controls">
          <label className="release-picker"><span>EDITION</span><select aria-label="Active curriculum release" value={atlas.releaseId || ''} onChange={(event) => chooseRelease(event.target.value)} disabled={atlas.selectingRelease || atlas.releaseLoading}>
            <option value="">{atlas.releaseLoading ? 'Finding releases…' : isNoActiveRelease(atlas.releaseError) ? 'Select a release' : 'No release'}</option>
            {atlas.releases.map((release) => <option key={release.release_id} value={release.release_id}>v{release.curriculum_version}{release.status ? ` · ${release.status.replaceAll('_', ' ')}` : ''}</option>)}
          </select></label>
          <div className="learner-chip" title={atlas.learnerError?.message || undefined}><span className="learner-chip__avatar">{atlas.learnerId ? 'A' : '·'}</span><span>{atlas.learnerName}</span>{isLearnerAmbiguous(atlas.learnerError) && <span className="learner-chip__warning">!</span>}</div>
        </div>
      </header>
      {connectionError && <div className="connection-banner" role="status"><span className="connection-banner__dot" />The local API is offline. Start the backend to load your curriculum.</div>}
      {atlas.releaseError && atlas.releaseError.status !== 0 && !isNoActiveRelease(atlas.releaseError) && <div className="connection-banner connection-banner--warning" role="status">{atlas.releaseError.message}</div>}
      <div className="route-view"><Outlet /></div>
      <nav className="mobile-nav" aria-label="Primary navigation">
        {nav.map((item) => <NavLink to={item.to} key={item.to} className={({ isActive }) => `mobile-nav__item${isActive ? ' mobile-nav__item--active' : ''}`}>
          <span className="mobile-nav__symbol" aria-hidden="true">{item.symbol}</span><span>{item.label}</span>
        </NavLink>)}
      </nav>
    </main>
  </div>
}

export function routeApiError(error: unknown) {
  return error instanceof ApiError ? error.message : 'Something went wrong while reading this part of the atlas.'
}
