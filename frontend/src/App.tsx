import {
  Route,
  Routes,
} from 'react-router-dom'

import AppLayout from './components/AppLayout'
import AccountPage from './pages/AccountPage'
import ConversationsPage from './pages/ConversationsPage'
import DirectConversationPage from './pages/DirectConversationPage'
import DirectMessagesIndexPage from './pages/DirectMessagesIndexPage'
import FriendsPage from './pages/FriendsPage'
import GroupConversationPage from './pages/GroupConversationPage'
import GroupChatsIndexPage from './pages/GroupChatsIndexPage'
import GroupDetailPage from './pages/GroupDetailPage'
import GroupJoinPage from './pages/GroupJoinPage'
import GroupsPage from './pages/GroupsPage'
import HomePage from './pages/HomePage'
import NotFoundPage from './pages/NotFoundPage'
import VoiceRoomDetailPage from './pages/VoiceRoomDetailPage'
import VoiceRoomJoinPage from './pages/VoiceRoomJoinPage'
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
          path="account"
          element={<AccountPage />}
        />

        <Route
          path="friends"
          element={<FriendsPage />}
        />

        <Route
          path="messages"
          element={<ConversationsPage />}
        >
          <Route
            index
            element={<DirectMessagesIndexPage />}
          />
          <Route
            path="dm/:conversationId"
            element={<DirectConversationPage />}
          />
        </Route>

        <Route
          path="groups"
          element={<GroupsPage />}
        >
          <Route
            index
            element={<GroupChatsIndexPage />}
          />
          <Route
            path=":groupId/messages"
            element={<GroupConversationPage />}
          />
        </Route>

        <Route
          path="groups/join/:token"
          element={<GroupJoinPage />}
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
          path="voice/join/:token"
          element={<VoiceRoomJoinPage />}
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
