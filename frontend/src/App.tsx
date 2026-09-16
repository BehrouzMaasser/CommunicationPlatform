import {
  Route,
  Routes,
} from 'react-router-dom'

import AppLayout from './components/AppLayout'
import ConversationsPage from './pages/ConversationsPage'
import DirectConversationPage from './pages/DirectConversationPage'
import FriendsPage from './pages/FriendsPage'
import GroupConversationPage from './pages/GroupConversationPage'
import GroupDetailPage from './pages/GroupDetailPage'
import GroupJoinPage from './pages/GroupJoinPage'
import GroupsPage from './pages/GroupsPage'
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'
import VoiceRoomDetailPage from './pages/VoiceRoomDetailPage'
import VoiceRoomsPage from './pages/VoiceRoomsPage'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          index
          element={<HomePage />}
        />

        <Route
          path="friends"
          element={<FriendsPage />}
        />

        <Route
          path="messages"
          element={<ConversationsPage />}
        />

        <Route
          path="messages/dm/:conversationId"
          element={<DirectConversationPage />}
        />

        <Route
          path="groups"
          element={<GroupsPage />}
        />

        <Route
          path="groups/join/:token"
          element={<GroupJoinPage />}
        />

        <Route
          path="groups/:groupId/messages"
          element={<GroupConversationPage />}
        />

        <Route
          path="groups/:groupId"
          element={<GroupDetailPage />}
        />

        <Route
          path="voice"
          element={<VoiceRoomsPage />}
        />

        <Route
          path="voice/rooms/:roomId"
          element={<VoiceRoomDetailPage />}
        />

        <Route
          path="*"
          element={<NotFoundPage />}
        />
      </Route>
    </Routes>
  )
}

export default App
