import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

import {
  RealtimeClient,
} from './client'

import type {
  ConversationType,
  RealtimeEventHandler,
  RealtimeStatus,
} from './types'


type PresenceState = {
  online: boolean
  expiresAt: string | null
}


type RealtimeContextValue = {
  client: RealtimeClient
  status: RealtimeStatus
  currentUserId?: number
  isUserOnline:
    (userId: number) => boolean
}


const RealtimeContext =
  createContext<
    RealtimeContextValue | null
  >(null)


type RealtimeProviderProps = {
  enabled: boolean
  currentUserId?: number
  children: ReactNode
}


export function RealtimeProvider({
  enabled,
  currentUserId,
  children,
}: RealtimeProviderProps) {
  const [client] =
    useState(
      () => new RealtimeClient(),
    )

  const [status, setStatus] =
    useState<RealtimeStatus>(
      client.getStatus(),
    )


  const [
    presenceByUserId,
    setPresenceByUserId,
  ] = useState<
    Map<number, PresenceState>
  >(() => new Map())

  const [
    presenceNow,
    setPresenceNow,
  ] = useState(
    () => Date.now(),
  )

  useEffect(
    () =>
      client.onStatus(
        setStatus,
      ),
    [client],
  )

  useEffect(() => {
    if (enabled) {
      client.connect()
    } else {
      client.disconnect()
    }

    return () => {
      client.disconnect()
    }
  }, [client, enabled])


  useEffect(() => {
    if (
      !enabled ||
      currentUserId === undefined
    ) {
      return
    }

    return client.onEvent<{
      message: {
        id: number
        sender: {
          id: number
        }
      }
    }>(
      'message.created',
      ({ payload }) => {
        if (
          payload.message.sender.id
          === currentUserId
          ||
          client.getStatus()
          !== 'connected'
        ) {
          return
        }

        client.acknowledgeDelivered(
          payload.message.id,
        )
      },
    )
  }, [
    client,
    currentUserId,
    enabled,
  ])

  useEffect(
    () =>
      client.onEvent<{
        user_id: number
        online: boolean
        expires_at:
          string | null
      }>(
        'presence.updated',
        ({ payload }) => {
          setPresenceByUserId(
            (current) => {
              const next =
                new Map(current)

              next.set(
                payload.user_id,
                {
                  online:
                    payload.online,
                  expiresAt:
                    payload.expires_at,
                },
              )

              return next
            },
          )
        },
      ),
    [client],
  )

  useEffect(() => {
    const timer =
      window.setInterval(
        () => {
          setPresenceNow(
            Date.now(),
          )
        },
        5000,
      )

    return () => {
      window.clearInterval(
        timer,
      )
    }
  }, [])

  useEffect(() => {
    if (
      currentUserId === undefined
    ) {
      return
    }

    return client.onEvent<{
      user_a: {
        id: number
      }
      user_b: {
        id: number
      }
    }>(
      'friendship.removed',
      ({ payload }) => {
        let otherUserId:
          number | null = null

        if (
          payload.user_a.id
          === currentUserId
        ) {
          otherUserId =
            payload.user_b.id
        } else if (
          payload.user_b.id
          === currentUserId
        ) {
          otherUserId =
            payload.user_a.id
        }

        if (
          otherUserId === null
        ) {
          return
        }

        setPresenceByUserId(
          (current) => {
            const next =
              new Map(current)

            next.delete(
              otherUserId,
            )

            return next
          },
        )
      },
    )
  }, [
    client,
    currentUserId,
  ])

  const isUserOnline =
    useCallback(
      (userId: number) => {
        const presence =
          presenceByUserId.get(
            userId,
          )

        if (
          !presence ||
          !presence.online ||
          !presence.expiresAt
        ) {
          return false
        }

        return (
          new Date(
            presence.expiresAt,
          ).getTime()
          > presenceNow
        )
      },
      [
        presenceByUserId,
        presenceNow,
      ],
    )

  return (
    <RealtimeContext.Provider
      value={{
        client,
        status,
        currentUserId,
        isUserOnline,
      }}
    >
      {children}
    </RealtimeContext.Provider>
  )
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
) {
  const {
    client,
    status,
  } = useRealtime()

  useEffect(() => {
    if (
      !enabled ||
      status !== 'connected' ||
      !Number.isInteger(
        conversationId,
      ) ||
      conversationId <= 0
    ) {
      return
    }

    client.subscribeConversation(
      conversationType,
      conversationId,
    )

    return () => {
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
    status,
  ])
}
