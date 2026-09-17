import VoiceCallOverlay from './VoiceCallOverlay'

import {
  useVoice,
} from '../../voice/useVoice'


function GlobalVoiceControls() {
  const { state } = useVoice()

  if (
    state.session?.status !== 'RINGING'
  ) {
    return null
  }

  return <VoiceCallOverlay />
}


export default GlobalVoiceControls
