import {
  createContext,
  type ReactNode,
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


type RealtimeContextValue = {
  client: RealtimeClient
  status: RealtimeStatus
}


const RealtimeContext =
  createContext<
    RealtimeContextValue | null
  >(null)


type RealtimeProviderProps = {
  enabled: boolean
  children: ReactNode
}


export function RealtimeProvider({
  enabled,
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

  return (
    <RealtimeContext.Provider
      value={{
        client,
        status,
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
