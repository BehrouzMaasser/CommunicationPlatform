import {
  useContext,
  useEffect,
} from 'react'

import {
  RealtimeContext,
} from './realtimeContextState'

import type {
  ConversationType,
  RealtimeEventHandler,
} from './types'


type RealtimeErrorPayload = {
  code: string
  detail: string
}


export function useRealtime() {
  const context =
    useContext(
      RealtimeContext,
    )

  if (!context) {
    throw new Error(
      'useRealtime must be used inside RealtimeProvider.',
    )
  }

  return context
}


export function useRealtimeEvent<
  Payload = unknown,
>(
  type: string,
  handler:
    RealtimeEventHandler<Payload>,
) {
  const { client } =
    useRealtime()

  useEffect(
    () =>
      client.onEvent(
        type,
        handler,
      ),
    [
      client,
      type,
      handler,
    ],
  )
}


export function useConversationRealtimeSubscription(
  conversationType:
    ConversationType,
  conversationId: number,
  enabled = true,
  onSubscriptionRejected?:
    () => void,
) {
  const {
    client,
    status,
  } = useRealtime()

  useEffect(() => {
    if (
      !enabled
      || status !== 'connected'
      || !Number.isInteger(
        conversationId,
      )
      || conversationId <= 0
    ) {
      return
    }

    const requestId =
      client.subscribeConversation(
        conversationType,
        conversationId,
      )

    if (requestId === null) {
      return
    }

    const stopListeningForErrors =
      client.onEvent<
        RealtimeErrorPayload
      >(
        'error',
        (event) => {
          if (
            event.request_id !==
              requestId
            ||
            event.payload.code !==
              'NOT_AUTHORIZED'
          ) {
            return
          }

          onSubscriptionRejected?.()
        },
      )

    return () => {
      stopListeningForErrors()

      if (
        client.getStatus()
        === 'connected'
      ) {
        client
          .unsubscribeConversation(
            conversationType,
            conversationId,
          )
      }
    }
  }, [
    client,
    conversationType,
    conversationId,
    enabled,
    onSubscriptionRejected,
    status,
  ])
}
