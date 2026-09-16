type CueNote = {
  frequency: number
  offset: number
  duration: number
  gain: number
}


let audioContext:
  AudioContext | null = null


function getAudioContext():
AudioContext | null {
  if (typeof window === 'undefined') {
    return null
  }

  if (
    audioContext === null
    || audioContext.state === 'closed'
  ) {
    audioContext =
      new AudioContext({
        latencyHint: 'interactive',
      })
  }

  return audioContext
}


export function primeVoiceRoomSounds():
void {
  const context =
    getAudioContext()

  if (
    !context
    || context.state !== 'suspended'
  ) {
    return
  }

  void context.resume().catch(
    () => {
      /*
       * Browser autoplay policy may still
       * require another user gesture.
       */
    },
  )
}


async function playCue(
  notes: CueNote[],
): Promise<void> {
  const context =
    getAudioContext()

  if (!context) {
    return
  }

  if (context.state === 'suspended') {
    try {
      await context.resume()
    } catch {
      return
    }
  }

  if (context.state !== 'running') {
    return
  }

  const now =
    context.currentTime + 0.01

  for (const note of notes) {
    const oscillator =
      context.createOscillator()

    const gain =
      context.createGain()

    const startsAt =
      now + note.offset

    const endsAt =
      startsAt + note.duration

    oscillator.type = 'sine'

    oscillator.frequency.setValueAtTime(
      note.frequency,
      startsAt,
    )

    gain.gain.setValueAtTime(
      0.0001,
      startsAt,
    )

    gain.gain.exponentialRampToValueAtTime(
      note.gain,
      startsAt + 0.012,
    )

    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      endsAt,
    )

    oscillator.connect(gain)
    gain.connect(context.destination)

    oscillator.start(startsAt)
    oscillator.stop(endsAt + 0.02)
  }
}


export function playVoiceRoomJoinSound():
void {
  /*
   * Short ascending chime.
   */
  void playCue([
    {
      frequency: 523.25,
      offset: 0,
      duration: 0.15,
      gain: 0.04,
    },
    {
      frequency: 783.99,
      offset: 0.11,
      duration: 0.18,
      gain: 0.045,
    },
  ])
}


export function playVoiceRoomLeaveSound():
void {
  /*
   * Short descending chime.
   */
  void playCue([
    {
      frequency: 659.25,
      offset: 0,
      duration: 0.14,
      gain: 0.04,
    },
    {
      frequency: 392,
      offset: 0.1,
      duration: 0.19,
      gain: 0.04,
    },
  ])
}
