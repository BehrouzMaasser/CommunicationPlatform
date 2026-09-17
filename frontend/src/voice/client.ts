import type {
  Participant,
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication,
  Room,
} from 'livekit-client'

import type {
  VoiceMediaCredentials,
} from '../types/voice'


type LiveKitModule =
  typeof import('livekit-client')


const MICROPHONE_OPTIONS = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
}


const MEDIA_PARTICIPANT_IDENTITY_PREFIX =
  'voice_participant_'


export function voiceMediaParticipantIdentity(
  participationId: string,
): string {
  return (
    MEDIA_PARTICIPANT_IDENTITY_PREFIX
    + participationId
      .replace(/-/g, '')
      .toLowerCase()
  )
}


type ActiveSpeakersListener = (
  participantIdentities: string[],
) => void


type AudioPlaybackRequiredListener = (
  required: boolean,
) => void


function clampVolume(
  value: number,
): number {
  if (!Number.isFinite(value)) {
    return 1
  }

  return Math.min(
    1,
    Math.max(0, value),
  )
}


export class VoiceMediaClient {
  private room: Room | null = null

  private liveKit:
    LiveKitModule | null = null

  private liveKitPromise:
    Promise<LiveKitModule> | null =
      null

  private connecting = false

  private audioElements =
    new Set<HTMLMediaElement>()

  private participantVolumes =
    new Map<string, number>()

  private outputMuted = false

  private activeSpeakersListener:
    ActiveSpeakersListener | null = null

  private audioPlaybackRequiredListener:
    AudioPlaybackRequiredListener | null =
      null


  get currentRoom(): Room | null {
    return this.room
  }


  get isConnected(): boolean {
    if (
      !this.room ||
      !this.liveKit
    ) {
      return false
    }

    return (
      this.room.state
      ===
      this.liveKit
        .ConnectionState
        .Connected
    )
  }


  setActiveSpeakersListener(
    listener:
      ActiveSpeakersListener | null,
  ): void {
    this.activeSpeakersListener =
      listener

    listener?.([])
  }


  setAudioPlaybackRequiredListener(
    listener:
      AudioPlaybackRequiredListener | null,
  ): void {
    this.audioPlaybackRequiredListener =
      listener

    listener?.(
      this.room !== null
      && !this.room.canPlaybackAudio,
    )
  }


  setOutputMuted(
    muted: boolean,
  ): void {
    this.outputMuted = muted

    for (const element of this.audioElements) {
      element.muted = muted
    }
  }


  setParticipantVolume(
    participationId: string,
    volume: number,
  ): void {
    const identity =
      voiceMediaParticipantIdentity(
        participationId,
      )

    const normalized =
      clampVolume(volume)

    this.participantVolumes.set(
      identity,
      normalized,
    )

    const participant =
      this.room
        ?.remoteParticipants
        .get(identity)

    participant?.setVolume(
      normalized,
    )
  }


  async connect(
    credentials:
      VoiceMediaCredentials,
  ): Promise<void> {
    if (
      this.room !== null
      || this.connecting
    ) {
      throw new Error(
        'Voice media is already connected or connecting.',
      )
    }

    this.connecting = true

    try {
      const liveKit =
        await this.loadLiveKit()

      const room =
        new liveKit.Room({
          adaptiveStream: false,
          dynacast: false,
          disconnectOnPageLeave:
            true,
          audioCaptureDefaults:
            MICROPHONE_OPTIONS,
        })

      this.room = room

      room.on(
        liveKit
          .RoomEvent
          .ActiveSpeakersChanged,
        this.handleActiveSpeakersChanged,
      )

      room.on(
        liveKit
          .RoomEvent
          .AudioPlaybackStatusChanged,
        this.handleAudioPlaybackStatusChanged,
      )

      room.on(
        liveKit
          .RoomEvent
          .TrackSubscribed,
        this.handleTrackSubscribed,
      )

      room.on(
        liveKit
          .RoomEvent
          .TrackUnsubscribed,
        this.handleTrackUnsubscribed,
      )

      try {
        await room.connect(
          credentials.server_url,
          credentials
            .participant_token,
          {
            autoSubscribe: true,
          },
        )

        this.emitAudioPlaybackRequired()
      } catch (error) {
        if (
          this.room === room
        ) {
          this.room = null
        }

        this.unbindRoom(room)

        await room.disconnect()

        throw error
      }
    } finally {
      this.connecting = false
    }
  }


  async startAudioPlayback():
  Promise<void> {
    if (!this.room) {
      throw new Error(
        'Voice media is not connected.',
      )
    }

    await this.room.startAudio()

    this.emitAudioPlaybackRequired()
  }


  async setMicrophoneEnabled(
    enabled: boolean,
  ): Promise<void> {
    if (!this.room) {
      throw new Error(
        'Voice media is not connected.',
      )
    }

    await (
      this.room
        .localParticipant
        .setMicrophoneEnabled(
          enabled,
          MICROPHONE_OPTIONS,
        )
    )
  }


  async disconnect():
  Promise<void> {
    const room = this.room

    this.room = null

    if (!room) {
      this.removeAudioElements()
      this.participantVolumes.clear()
      this.emitActiveSpeakers([])
      this.emitAudioPlaybackRequired()
      return
    }

    /*
     * Explicitly release microphone capture before
     * disconnecting the room. Room.disconnect(true)
     * normally stops local tracks as well, but some
     * mobile Safari/iOS combinations can otherwise
     * leave the microphone recording indicator active.
     */
    try {
      await room
        .localParticipant
        .setMicrophoneEnabled(false)
    } catch {
      /*
       * Teardown must continue even if signaling has
       * already disappeared.
       */
    }

    this.stopLocalMicrophone(room)

    this.unbindRoom(room)

    this.removeAudioElements()
    this.participantVolumes.clear()
    this.emitActiveSpeakers([])
    this.emitAudioPlaybackRequired()

    await room.disconnect(true)
  }


  private stopLocalMicrophone(
    room: Room,
  ): void {
    const liveKit = this.liveKit

    if (!liveKit) {
      return
    }

    const publication =
      room.localParticipant
        .getTrackPublication(
          liveKit.Track.Source.Microphone,
        )

    const track =
      publication?.track

    if (!track) {
      return
    }

    /*
     * LocalTrack.stop() releases LiveKit's managed
     * capture track. Stop the underlying browser track
     * defensively as well so WebKit cannot keep the
     * physical microphone source alive.
     */
    track.stop()

    if (
      track.mediaStreamTrack
        .readyState !== 'ended'
    ) {
      track.mediaStreamTrack.stop()
    }
  }


  private async loadLiveKit():
  Promise<LiveKitModule> {
    if (this.liveKit) {
      return this.liveKit
    }

    if (!this.liveKitPromise) {
      this.liveKitPromise =
        import('livekit-client')
    }

    try {
      const liveKit =
        await this.liveKitPromise

      this.liveKit = liveKit

      return liveKit
    } finally {
      this.liveKitPromise = null
    }
  }


  private readonly handleAudioPlaybackStatusChanged =
    (): void => {
      this.emitAudioPlaybackRequired()
    }


  private emitAudioPlaybackRequired():
  void {
    this.audioPlaybackRequiredListener?.(
      this.room !== null
      && !this.room.canPlaybackAudio,
    )
  }


  private readonly handleActiveSpeakersChanged = (
    speakers: Participant[],
  ): void => {
    this.emitActiveSpeakers(
      speakers.map(
        (participant) =>
          participant.identity,
      ),
    )
  }


  private emitActiveSpeakers(
    participantIdentities: string[],
  ): void {
    this.activeSpeakersListener?.(
      participantIdentities,
    )
  }


  private readonly handleTrackSubscribed = (
    track: RemoteTrack,
    _publication: RemoteTrackPublication,
    participant: RemoteParticipant,
  ): void => {
    const liveKit = this.liveKit

    if (
      !liveKit
      ||
      track.kind
      !== liveKit.Track.Kind.Audio
    ) {
      return
    }

    const volume =
      this.participantVolumes.get(
        participant.identity,
      )

    if (volume !== undefined) {
      participant.setVolume(volume)
    }

    const element =
      track.attach()

    element.autoplay = true
    element.muted = this.outputMuted

    element.setAttribute(
      'data-voice-audio',
      'true',
    )

    this.audioElements.add(
      element,
    )

    document.body.appendChild(
      element,
    )
  }


  private readonly handleTrackUnsubscribed = (
    track: RemoteTrack,
  ): void => {
    const elements =
      track.detach()

    for (
      const element
      of elements
    ) {
      element.remove()

      this.audioElements.delete(
        element,
      )
    }
  }


  private unbindRoom(
    room: Room,
  ): void {
    const liveKit = this.liveKit

    if (!liveKit) {
      return
    }

    room.off(
      liveKit
        .RoomEvent
        .ActiveSpeakersChanged,
      this.handleActiveSpeakersChanged,
    )

    room.off(
      liveKit
        .RoomEvent
        .AudioPlaybackStatusChanged,
      this.handleAudioPlaybackStatusChanged,
    )

    room.off(
      liveKit
        .RoomEvent
        .TrackSubscribed,
      this.handleTrackSubscribed,
    )

    room.off(
      liveKit
        .RoomEvent
        .TrackUnsubscribed,
      this.handleTrackUnsubscribed,
    )
  }


  private removeAudioElements():
  void {
    for (
      const element
      of this.audioElements
    ) {
      element.remove()
    }

    this.audioElements.clear()
  }
}


export const voiceMediaClient =
  new VoiceMediaClient()
