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



export function applyDeliveredReceipt(
  messages: Message[],
  {
    messageId,
    userId,
    deliveredAt,
  }: {
    messageId: number
    userId: number
    deliveredAt: string
  },
): Message[] {
  return messages.map(
    (message) => {
      if (
        message.id !== messageId
      ) {
        return message
      }

      return {
        ...message,
        receipts:
          message.receipts.map(
            (receipt) =>
              receipt.user.id ===
                userId
                ? {
                    ...receipt,
                    delivered_at:
                      receipt
                        .delivered_at
                      ?? deliveredAt,
                  }
                : receipt,
          ),
      }
    },
  )
}


export function applyReadThroughReceipt(
  messages: Message[],
  {
    throughMessageId,
    userId,
    readAt,
  }: {
    throughMessageId: number
    userId: number
    readAt: string
  },
): Message[] {
  const throughIndex =
    messages.findIndex(
      (message) =>
        message.id ===
        throughMessageId,
    )

  if (throughIndex < 0) {
    return messages
  }

  return messages.map(
    (message, index) => {
      if (index > throughIndex) {
        return message
      }

      return {
        ...message,
        receipts:
          message.receipts.map(
            (receipt) =>
              receipt.user.id ===
                userId
                ? {
                    ...receipt,
                    delivered_at:
                      receipt
                        .delivered_at
                      ?? readAt,
                    read_at:
                      receipt.read_at
                      ?? readAt,
                  }
                : receipt,
          ),
      }
    },
  )
}
