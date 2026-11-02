import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './AppShell'
import { ExplorePage } from '../features/explore/ExplorePage'
import { ProgressPage } from '../features/progress/ProgressPage'
import { AtlasSurveyPage } from '../features/atlas/AtlasSurveyPage'
import { TopicPage } from '../features/topic/TopicPage'

export function App() {
  return <Routes>
    <Route element={<AppShell />}>
      <Route index element={<Navigate to="/roadmap" replace />} />
      <Route path="roadmap" element={<AtlasSurveyPage />} />
      <Route path="topics" element={<ExplorePage />} />
      <Route path="topics/:topicId" element={<TopicPage />} />
      <Route path="progress" element={<ProgressPage />} />
      <Route path="*" element={<Navigate to="/roadmap" replace />} />
    </Route>
  </Routes>
}
