import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import {
  useRealtime,
  useRealtimeEvent,
} from './useRealtime'

import type {
  ConversationType,
} from './types'


type TypingPayload = {
  conversation_type:
    ConversationType
  conversation_id: number
  user_id: number
  username: string
}


type TypingUser = {
  username: string
  expiresAt: number
}


export function useConversationTyping(
  conversationType:
    ConversationType,
  conversationId: number,
) {
  const {
    client,
    currentUserId,
    status,
  } = useRealtime()

  const [
    typingUsers,
    setTypingUsers,
  ] = useState<
    Map<number, TypingUser>
  >(() => new Map())

  const typingActive =
    useRef(false)

  const lastStartSentAt =
    useRef(0)

  const stopTimer =
    useRef<number | null>(
      null,
    )

  const handleStarted =
    useCallback(
      ({
        payload,
      }: {
        payload: TypingPayload
      }) => {
        if (
          payload
            .conversation_type
            !== conversationType
          ||
          payload
            .conversation_id
            !== conversationId
          ||
          payload.user_id
            === currentUserId
        ) {
          return
        }

        setTypingUsers(
          (current) => {
            const next =
              new Map(current)

            next.set(
              payload.user_id,
              {
                username:
                  payload.username,
                expiresAt:
                  Date.now()
                  + 6000,
              },
            )

            return next
          },
        )
      },
      [
        conversationId,
        conversationType,
        currentUserId,
      ],
    )

  const handleStopped =
    useCallback(
      ({
        payload,
      }: {
        payload: TypingPayload
      }) => {
        if (
          payload
            .conversation_type
            !== conversationType
          ||
          payload
            .conversation_id
            !== conversationId
        ) {
          return
        }

        setTypingUsers(
          (current) => {
            if (
              !current.has(
                payload.user_id,
              )
            ) {
              return current
            }

            const next =
              new Map(current)

            next.delete(
              payload.user_id,
            )

            return next
          },
        )
      },
      [
        conversationId,
        conversationType,
      ],
    )

  useRealtimeEvent<TypingPayload>(
    'typing.started',
    handleStarted,
  )

  useRealtimeEvent<TypingPayload>(
    'typing.stopped',
    handleStopped,
  )

  const stopTyping =
    useCallback(
      () => {
        if (
          stopTimer.current
          !== null
        ) {
          window.clearTimeout(
            stopTimer.current,
          )
          stopTimer.current = null
        }

        if (!typingActive.current) {
          return
        }

        typingActive.current = false

        if (
          client.getStatus() ===
            'connected'
        ) {
          client.stopTyping(
            conversationType,
            conversationId,
          )
        }
      },
      [
        client,
        conversationId,
        conversationType,
      ],
    )

  const notifyTyping =
    useCallback(
      () => {
        if (
          client.getStatus() !==
            'connected'
        ) {
          return
        }

        const now = Date.now()

        if (
          !typingActive.current
          ||
          now
          - lastStartSentAt.current
          >= 3000
        ) {
          const requestId =
            client.startTyping(
              conversationType,
              conversationId,
            )

          if (requestId === null) {
            return
          }

          lastStartSentAt.current =
            now
        }

        typingActive.current = true

        if (
          stopTimer.current
          !== null
        ) {
          window.clearTimeout(
            stopTimer.current,
          )
        }

        stopTimer.current =
          window.setTimeout(
            stopTyping,
            2000,
          )
      },
      [
        client,
        conversationId,
        conversationType,
        stopTyping,
      ],
    )

  useEffect(() => {
    if (status === 'connected') {
      return
    }

    if (
      stopTimer.current !== null
    ) {
      window.clearTimeout(
        stopTimer.current,
      )
      stopTimer.current = null
    }

    typingActive.current = false
    lastStartSentAt.current = 0
  }, [status])


  useEffect(() => {
    const timer =
      window.setInterval(
        () => {
          const now =
            Date.now()

          setTypingUsers(
            (current) => {
              let changed = false
              const next =
                new Map(current)

              for (
                const [
                  userId,
                  typingUser,
                ]
                of next
              ) {
                if (
                  typingUser
                    .expiresAt
                  <= now
                ) {
                  next.delete(
                    userId,
                  )
                  changed = true
                }
              }

              return changed
                ? next
                : current
            },
          )
        },
        1000,
      )

    return () => {
      window.clearInterval(
        timer,
      )
    }
  }, [])

  useEffect(
    () => () => {
      stopTyping()
    },
    [stopTyping],
  )

  return {
    typingUsernames:
      Array.from(
        typingUsers.values(),
      ).map(
        (user) =>
          user.username,
      ),
    notifyTyping,
    stopTyping,
  }
}
