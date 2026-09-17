import type {
  ReactNode,
} from 'react'

import {
  ActivityProvider,
} from '../activity/ActivityContext'
import {
  RealtimeProvider,
} from '../realtime/RealtimeContext'
import {
  useSession,
} from '../session/useSession'
import {
  VoiceProvider,
} from '../voice/VoiceContext'

import GlobalVoiceControls from './voice/GlobalVoiceControls'


type ApplicationRuntimeProps = {
  children: ReactNode
}


function ApplicationRuntime({
  children,
}: ApplicationRuntimeProps) {
  const {
    authStatus,
    currentUser,
  } = useSession()

  const enabled =
    authStatus === 'authenticated'

  return (
    <RealtimeProvider
      enabled={enabled}
      currentUserId={currentUser?.id}
    >
      <VoiceProvider
        key={
          currentUser?.id
          ?? 'anonymous'
        }
        enabled={enabled}
        currentUserId={currentUser?.id}
      >
        <ActivityProvider
          enabled={enabled}
          currentUserId={currentUser?.id}
        >
          {children}
          <GlobalVoiceControls />
        </ActivityProvider>
      </VoiceProvider>
    </RealtimeProvider>
  )
}


export default ApplicationRuntime
