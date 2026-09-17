const OUTPUT_VOLUME_PREFIX =
  'communication-platform.voice.output-volume'

const OUTPUT_DEVICE_PREFIX =
  'communication-platform.voice.output-device'

const MICROPHONE_NOISE_GATE_THRESHOLD_PREFIX =
  'communication-platform.voice.microphone-noise-gate-threshold-db'

const SESSION_MEDIA_PREFERENCES_KEY =
  'communication-platform.voice.session-media-preferences'


export const DEFAULT_VOICE_OUTPUT_VOLUME = 1


export type VoiceSessionMediaPreferences = {
  currentUserId: number
  sessionId: string
  microphoneEnabled: boolean
  audioOutputMuted: boolean
}


export function normalizeVoiceOutputVolume(
  value: number,
): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_VOICE_OUTPUT_VOLUME
  }

  return Math.min(
    1,
    Math.max(0, value),
  )
}


function userPreferenceKey(
  prefix: string,
  currentUserId: number,
): string {
  return `${prefix}.${currentUserId}`
}


export function readVoiceOutputVolume(
  currentUserId: number | null,
): number {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return DEFAULT_VOICE_OUTPUT_VOLUME
  }

  try {
    const raw =
      window.localStorage.getItem(
        userPreferenceKey(
          OUTPUT_VOLUME_PREFIX,
          currentUserId,
        ),
      )

    if (raw === null) {
      return DEFAULT_VOICE_OUTPUT_VOLUME
    }

    return normalizeVoiceOutputVolume(
      Number(raw),
    )
  } catch {
    return DEFAULT_VOICE_OUTPUT_VOLUME
  }
}


export function writeVoiceOutputVolume(
  currentUserId: number | null,
  value: number,
): void {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return
  }

  const normalized =
    normalizeVoiceOutputVolume(value)

  try {
    const key =
      userPreferenceKey(
        OUTPUT_VOLUME_PREFIX,
        currentUserId,
      )

    if (
      normalized
      === DEFAULT_VOICE_OUTPUT_VOLUME
    ) {
      window.localStorage.removeItem(key)
      return
    }

    window.localStorage.setItem(
      key,
      String(normalized),
    )
  } catch {
    /* Current-session audio still works without storage. */
  }
}


export function readVoiceOutputDeviceId(
  currentUserId: number | null,
): string {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return ''
  }

  try {
    return (
      window.localStorage.getItem(
        userPreferenceKey(
          OUTPUT_DEVICE_PREFIX,
          currentUserId,
        ),
      )
      ?? ''
    )
  } catch {
    return ''
  }
}


export function writeVoiceOutputDeviceId(
  currentUserId: number | null,
  deviceId: string,
): void {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return
  }

  try {
    const key =
      userPreferenceKey(
        OUTPUT_DEVICE_PREFIX,
        currentUserId,
      )

    if (!deviceId) {
      window.localStorage.removeItem(key)
      return
    }

    window.localStorage.setItem(
      key,
      deviceId,
    )
  } catch {
    /* Current-session routing still works without storage. */
  }
}


export function readVoiceNoiseGateThresholdDb(
  currentUserId: number | null,
): number | null {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return null
  }

  try {
    const raw =
      window.localStorage.getItem(
        userPreferenceKey(
          MICROPHONE_NOISE_GATE_THRESHOLD_PREFIX,
          currentUserId,
        ),
      )

    if (raw === null) {
      return null
    }

    const value = Number(raw)

    if (!Number.isFinite(value)) {
      return null
    }

    return Math.min(
      -20,
      Math.max(-60, Math.round(value)),
    )
  } catch {
    return null
  }
}


export function writeVoiceNoiseGateThresholdDb(
  currentUserId: number | null,
  value: number | null,
): void {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return
  }

  try {
    const key =
      userPreferenceKey(
        MICROPHONE_NOISE_GATE_THRESHOLD_PREFIX,
        currentUserId,
      )

    if (value === null) {
      window.localStorage.removeItem(key)
      return
    }

    const normalized = Math.min(
      -20,
      Math.max(-60, Math.round(value)),
    )

    window.localStorage.setItem(
      key,
      String(normalized),
    )
  } catch {
    /* Current-session input processing still works without storage. */
  }
}


export function readVoiceSessionMediaPreferences(
  currentUserId: number | null,
  sessionId: string,
): VoiceSessionMediaPreferences | null {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return null
  }

  try {
    const raw =
      window.sessionStorage.getItem(
        SESSION_MEDIA_PREFERENCES_KEY,
      )

    if (!raw) {
      return null
    }

    const parsed =
      JSON.parse(raw) as Partial<VoiceSessionMediaPreferences>

    if (
      parsed.currentUserId !== currentUserId
      || parsed.sessionId !== sessionId
      || typeof parsed.microphoneEnabled
        !== 'boolean'
      || typeof parsed.audioOutputMuted
        !== 'boolean'
    ) {
      return null
    }

    return parsed as VoiceSessionMediaPreferences
  } catch {
    return null
  }
}


export function writeVoiceSessionMediaPreferences(
  preferences: VoiceSessionMediaPreferences,
): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.setItem(
      SESSION_MEDIA_PREFERENCES_KEY,
      JSON.stringify(preferences),
    )
  } catch {
    /* Recovery falls back to safe defaults without storage. */
  }
}


export function clearVoiceSessionMediaPreferences(
  currentUserId: number | null,
  sessionId?: string,
): void {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return
  }

  try {
    if (!sessionId) {
      window.sessionStorage.removeItem(
        SESSION_MEDIA_PREFERENCES_KEY,
      )
      return
    }

    const current =
      readVoiceSessionMediaPreferences(
        currentUserId,
        sessionId,
      )

    if (current) {
      window.sessionStorage.removeItem(
        SESSION_MEDIA_PREFERENCES_KEY,
      )
    }
  } catch {
    /* Nothing to clear. */
  }
}
