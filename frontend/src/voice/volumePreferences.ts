const STORAGE_PREFIX =
  'communication-platform.voice.volume'


export const DEFAULT_VOICE_PARTICIPANT_VOLUME = 1


export function normalizeVoiceParticipantVolume(
  value: number,
): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_VOICE_PARTICIPANT_VOLUME
  }

  return Math.min(
    1,
    Math.max(0, value),
  )
}


function preferenceKey(
  currentUserId: number,
  targetUserId: number,
): string {
  return (
    `${STORAGE_PREFIX}.`
    + `${currentUserId}.`
    + `${targetUserId}`
  )
}


function lastNonZeroPreferenceKey(
  currentUserId: number,
  targetUserId: number,
): string {
  return (
    `${preferenceKey(
      currentUserId,
      targetUserId,
    )}.last-nonzero`
  )
}


export function readVoiceParticipantVolume(
  currentUserId: number | null,
  targetUserId: number,
): number {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return DEFAULT_VOICE_PARTICIPANT_VOLUME
  }

  try {
    const raw =
      window.localStorage.getItem(
        preferenceKey(
          currentUserId,
          targetUserId,
        ),
      )

    if (raw === null) {
      return DEFAULT_VOICE_PARTICIPANT_VOLUME
    }

    return normalizeVoiceParticipantVolume(
      Number(raw),
    )
  } catch {
    return DEFAULT_VOICE_PARTICIPANT_VOLUME
  }
}


export function readLastNonZeroVoiceParticipantVolume(
  currentUserId: number | null,
  targetUserId: number,
): number {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return DEFAULT_VOICE_PARTICIPANT_VOLUME
  }

  try {
    const raw =
      window.localStorage.getItem(
        lastNonZeroPreferenceKey(
          currentUserId,
          targetUserId,
        ),
      )

    if (raw === null) {
      return DEFAULT_VOICE_PARTICIPANT_VOLUME
    }

    const value =
      normalizeVoiceParticipantVolume(
        Number(raw),
      )

    return value > 0
      ? value
      : DEFAULT_VOICE_PARTICIPANT_VOLUME
  } catch {
    return DEFAULT_VOICE_PARTICIPANT_VOLUME
  }
}


export function writeVoiceParticipantVolume(
  currentUserId: number | null,
  targetUserId: number,
  value: number,
): void {
  if (
    currentUserId === null
    || typeof window === 'undefined'
  ) {
    return
  }

  const normalized =
    normalizeVoiceParticipantVolume(
      value,
    )

  try {
    const key =
      preferenceKey(
        currentUserId,
        targetUserId,
      )

    const lastNonZeroKey =
      lastNonZeroPreferenceKey(
        currentUserId,
        targetUserId,
      )

    if (
      normalized ===
      DEFAULT_VOICE_PARTICIPANT_VOLUME
    ) {
      window.localStorage.removeItem(key)
      window.localStorage.removeItem(
        lastNonZeroKey,
      )
      return
    }

    window.localStorage.setItem(
      key,
      String(normalized),
    )

    if (normalized > 0) {
      window.localStorage.setItem(
        lastNonZeroKey,
        String(normalized),
      )
    }
  } catch {
    /*
     * Volume still works for the current session
     * if browser storage is unavailable.
     */
  }
}
