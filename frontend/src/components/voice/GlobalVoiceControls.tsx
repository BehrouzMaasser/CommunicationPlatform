import VoiceCallOverlay from './VoiceCallOverlay'
import VoiceRoomOverlay from './VoiceRoomOverlay'

import {
  useVoice,
} from '../../voice/useVoice'


function GlobalVoiceControls() {
  const { state } = useVoice()

  return (
    <>
      <VoiceCallOverlay />
      <VoiceRoomOverlay
        key={
          state.session?.kind === 'ROOM'
            ? state.session.id
            : 'voice-room-idle'
        }
      />
    </>
  )
}


export default GlobalVoiceControls
