import type {
  LocalAudioTrack,
  Participant,
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication,
  Room,
  TrackPublication,
} from 'livekit-client'

import type {
  VoiceMediaCredentials,
} from '../types/voice'

import {
  VoiceNoiseGateProcessor,
  normalizeVoiceNoiseGateThresholdDb,
} from './noiseGateProcessor'


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


type MutedMicrophonesListener = (
  participantIdentities: string[],
) => void


export type VoiceMediaConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'


type ConnectionStatusListener = (
  status: VoiceMediaConnectionStatus,
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

  private outputVolume = 1

  private microphoneNoiseGateThresholdDb:
    number | null = null

  private noiseGateProcessor:
    VoiceNoiseGateProcessor | null = null

  private activeSpeakersListener:
    ActiveSpeakersListener | null = null

  private audioPlaybackRequiredListener:
    AudioPlaybackRequiredListener | null =
      null

  private mutedMicrophonesListener:
    MutedMicrophonesListener | null = null

  private connectionStatusListener:
    ConnectionStatusListener | null = null


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


  setMutedMicrophonesListener(
    listener:
      MutedMicrophonesListener | null,
  ): void {
    this.mutedMicrophonesListener =
      listener

    this.emitMutedMicrophones()
  }


  setConnectionStatusListener(
    listener:
      ConnectionStatusListener | null,
  ): void {
    this.connectionStatusListener =
      listener

    listener?.(
      this.isConnected
        ? 'connected'
        : this.connecting
          ? 'connecting'
          : 'disconnected',
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


  setOutputVolume(
    volume: number,
  ): void {
    this.outputVolume =
      clampVolume(volume)

    for (
      const participant
      of this.room
        ?.remoteParticipants
        .values() ?? []
    ) {
      const participantVolume =
        this.participantVolumes.get(
          participant.identity,
        ) ?? 1

      participant.setVolume(
        participantVolume
        * this.outputVolume,
      )
    }
  }


  async switchAudioOutputDevice(
    deviceId: string,
  ): Promise<boolean> {
    if (!this.room) {
      throw new Error(
        'Voice media is not connected.',
      )
    }

    return this.room
      .switchActiveDevice(
        'audiooutput',
        deviceId,
      )
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
      normalized
      * this.outputVolume,
    )
  }


  async setMicrophoneNoiseGateThresholdDb(
    thresholdDb: number | null,
  ): Promise<void> {
    this.microphoneNoiseGateThresholdDb =
      normalizeVoiceNoiseGateThresholdDb(
        thresholdDb,
      )

    await this.applyMicrophoneNoiseGate()
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
    this.emitConnectionStatus(
      'connecting',
    )

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

      room.on(
        liveKit
          .RoomEvent
          .TrackMuted,
        this.handleTrackMuteChanged,
      )

      room.on(
        liveKit
          .RoomEvent
          .TrackUnmuted,
        this.handleTrackMuteChanged,
      )

      room.on(
        liveKit
          .RoomEvent
          .ParticipantConnected,
        this.handleParticipantConnected,
      )

      room.on(
        liveKit
          .RoomEvent
          .ParticipantDisconnected,
        this.handleParticipantDisconnected,
      )

      room.on(
        liveKit
          .RoomEvent
          .Reconnecting,
        this.handleRoomReconnecting,
      )

      room.on(
        liveKit
          .RoomEvent
          .Reconnected,
        this.handleRoomReconnected,
      )

      room.on(
        liveKit
          .RoomEvent
          .Disconnected,
        this.handleRoomDisconnected,
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
        this.emitMutedMicrophones()
        this.emitConnectionStatus(
          'connected',
        )
      } catch (error) {
        if (
          this.room === room
        ) {
          this.room = null
        }

        this.unbindRoom(room)

        await room.disconnect()

        this.emitConnectionStatus(
          'disconnected',
        )

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

    if (enabled) {
      await this.applyMicrophoneNoiseGate()
    }
  }


  async disconnect():
  Promise<void> {
    const room = this.room

    this.room = null

    if (!room) {
      this.removeAudioElements()
      this.participantVolumes.clear()
      this.noiseGateProcessor = null
      this.emitActiveSpeakers([])
      this.emitMutedMicrophones()
      this.emitAudioPlaybackRequired()
      this.emitConnectionStatus(
        'disconnected',
      )
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
    this.noiseGateProcessor = null
    this.emitActiveSpeakers([])
    this.emitMutedMicrophones()
    this.emitAudioPlaybackRequired()

    await room.disconnect(true)

    this.emitConnectionStatus(
      'disconnected',
    )
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


  private readonly handleRoomReconnecting =
    (): void => {
      this.emitConnectionStatus(
        'connecting',
      )
    }


  private readonly handleRoomReconnected =
    (): void => {
      this.emitConnectionStatus(
        'connected',
      )
    }


  private readonly handleRoomDisconnected =
    (): void => {
      const room = this.room

      if (!room) {
        this.emitConnectionStatus(
          'disconnected',
        )
        return
      }

      this.room = null
      this.stopLocalMicrophone(room)
      this.unbindRoom(room)
      this.removeAudioElements()
      this.noiseGateProcessor = null
      this.emitActiveSpeakers([])
      this.emitMutedMicrophones()
      this.emitAudioPlaybackRequired()
      this.emitConnectionStatus(
        'disconnected',
      )
    }


  private readonly handleTrackMuteChanged = (
    publication: TrackPublication,
  ): void => {
    const liveKit = this.liveKit

    if (
      !liveKit
      || publication.source
        !== liveKit.Track.Source.Microphone
    ) {
      return
    }

    this.emitMutedMicrophones()
  }


  private readonly handleParticipantConnected =
    (): void => {
      this.emitMutedMicrophones()
    }


  private readonly handleParticipantDisconnected =
    (): void => {
      this.emitMutedMicrophones()
    }


  private emitMutedMicrophones(): void {
    const liveKit = this.liveKit
    const room = this.room

    if (!liveKit || !room) {
      this.mutedMicrophonesListener?.([])
      return
    }

    const identities: string[] = []

    for (
      const participant
      of room.remoteParticipants.values()
    ) {
      const publication =
        participant.getTrackPublication(
          liveKit.Track.Source.Microphone,
        )

      if (
        !publication
        || publication.isMuted
      ) {
        identities.push(
          participant.identity,
        )
      }
    }

    this.mutedMicrophonesListener?.(
      identities,
    )
  }


  private async applyMicrophoneNoiseGate():
  Promise<void> {
    const liveKit = this.liveKit
    const room = this.room

    if (!liveKit || !room) {
      return
    }

    const publication =
      room.localParticipant
        .getTrackPublication(
          liveKit.Track.Source.Microphone,
        )

    const track = publication?.track

    if (
      !track
      || track.kind
        !== liveKit.Track.Kind.Audio
    ) {
      return
    }

    const audioTrack =
      track as LocalAudioTrack

    const threshold =
      this.microphoneNoiseGateThresholdDb

    const currentProcessor =
      audioTrack.getProcessor()

    if (threshold === null) {
      if (
        currentProcessor?.name
        === 'communication-platform-noise-gate'
      ) {
        await audioTrack.stopProcessor()
      }

      this.noiseGateProcessor = null
      return
    }

    if (
      currentProcessor?.name
      === 'communication-platform-noise-gate'
      && this.noiseGateProcessor
    ) {
      this.noiseGateProcessor
        .setThresholdDb(threshold)
      return
    }

    const processor =
      new VoiceNoiseGateProcessor(
        threshold,
      )

    await audioTrack.setProcessor(processor)

    this.noiseGateProcessor = processor
  }


  private readonly handleAudioPlaybackStatusChanged =
    (): void => {
      this.emitAudioPlaybackRequired()
    }


  private emitConnectionStatus(
    status: VoiceMediaConnectionStatus,
  ): void {
    this.connectionStatusListener?.(
      status,
    )
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

    participant.setVolume(
      (volume ?? 1)
      * this.outputVolume,
    )

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

    this.emitMutedMicrophones()
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

    this.emitMutedMicrophones()
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

    room.off(
      liveKit
        .RoomEvent
        .TrackMuted,
      this.handleTrackMuteChanged,
    )

    room.off(
      liveKit
        .RoomEvent
        .TrackUnmuted,
      this.handleTrackMuteChanged,
    )

    room.off(
      liveKit
        .RoomEvent
        .ParticipantConnected,
      this.handleParticipantConnected,
    )

    room.off(
      liveKit
        .RoomEvent
        .ParticipantDisconnected,
      this.handleParticipantDisconnected,
    )

    room.off(
      liveKit
        .RoomEvent
        .Reconnecting,
      this.handleRoomReconnecting,
    )

    room.off(
      liveKit
        .RoomEvent
        .Reconnected,
      this.handleRoomReconnected,
    )

    room.off(
      liveKit
        .RoomEvent
        .Disconnected,
      this.handleRoomDisconnected,
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
