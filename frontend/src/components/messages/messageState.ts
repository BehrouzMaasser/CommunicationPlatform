import type {
  Message,
} from '../../types/messages'


function compareMessages(
  left: Message,
  right: Message,
): number {
  const timeDifference =
    new Date(
      left.created_at,
    ).getTime()
    -
    new Date(
      right.created_at,
    ).getTime()

  if (
    Number.isFinite(
      timeDifference,
    ) &&
    timeDifference !== 0
  ) {
    return timeDifference
  }

  return left.id - right.id
}


export function mergeMessage(
  current: Message[],
  incoming: Message,
): Message[] {
  const existingIndex =
    current.findIndex(
      (message) =>
        message.id ===
        incoming.id,
    )

  if (existingIndex === -1) {
    return [
      ...current,
      incoming,
    ].sort(compareMessages)
  }

  const next = [...current]

  next[existingIndex] =
    incoming

  return next.sort(
    compareMessages,
  )
}


export function mergeMessageList(
  current: Message[],
  incoming: Message[],
): Message[] {
  let merged = current

  for (
    const message
    of incoming
  ) {
    merged = mergeMessage(
      merged,
      message,
    )
  }

  return merged
}
