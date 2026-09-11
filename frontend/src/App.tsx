import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ConversationsPage from './pages/ConversationsPage'
import FriendsPage from './pages/FriendsPage'
import GroupsPage from './pages/GroupsPage'
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="friends" element={<FriendsPage />} />
        <Route path="messages" element={<ConversationsPage />} />
        <Route path="groups" element={<GroupsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
