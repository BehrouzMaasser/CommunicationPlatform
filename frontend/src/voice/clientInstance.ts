const STORAGE_KEY =
  'communication-platform.voice.client-instance-id'

let inMemoryClientInstanceId:
  string | null = null


function createClientInstanceId():
string {
  return crypto.randomUUID()
}


export function getVoiceClientInstanceId():
string {
  if (inMemoryClientInstanceId) {
    return inMemoryClientInstanceId
  }

  try {
    const stored =
      sessionStorage.getItem(
        STORAGE_KEY,
      )

    if (stored) {
      inMemoryClientInstanceId =
        stored

      return stored
    }

    const created =
      createClientInstanceId()

    sessionStorage.setItem(
      STORAGE_KEY,
      created,
    )

    inMemoryClientInstanceId =
      created

    return created
  } catch {
    /*
     * sessionStorage can be unavailable in unusually
     * restrictive browser contexts. Keep this page
     * functional with an in-memory identity.
     */
    const created =
      createClientInstanceId()

    inMemoryClientInstanceId =
      created

    return created
  }
}
