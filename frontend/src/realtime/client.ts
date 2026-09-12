import type {
  ConversationType,
  RealtimeEvent,
  RealtimeEventHandler,
  RealtimeStatus,
} from './types'


type StatusHandler = (
  status: RealtimeStatus,
) => void


function createRequestId(): string {
  return crypto.randomUUID()
}


function websocketUrl(): string {
  const protocol =
    window.location.protocol === 'https:'
      ? 'wss:'
      : 'ws:'

  return (
    `${protocol}//${window.location.host}/ws/v1/`
  )
}


export class RealtimeClient {
  private socket: WebSocket | null =
    null

  private status:
    RealtimeStatus =
      'disconnected'

  private manuallyStopped = false

  private reconnectTimer:
    number | null = null

  private reconnectAttempt = 0

  private heartbeatTimer:
    number | null = null

  private eventHandlers =
    new Map<
      string,
      Set<RealtimeEventHandler>
    >()

  private statusHandlers =
    new Set<StatusHandler>()

  private seenEventIds =
    new Set<string>()

  private seenEventOrder:
    string[] = []

  connect() {
    if (
      this.socket &&
      (
        this.socket.readyState ===
          WebSocket.OPEN ||
        this.socket.readyState ===
          WebSocket.CONNECTING
      )
    ) {
      return
    }

    this.manuallyStopped = false
    this.setStatus('connecting')

    const socket =
      new WebSocket(
        websocketUrl(),
      )

    this.socket = socket

    socket.addEventListener(
      'open',
      () => {
        this.reconnectAttempt = 0
        this.setStatus('connected')
        this.startHeartbeat()
      },
    )

    socket.addEventListener(
      'message',
      (message) => {
        this.handleMessage(
          message.data,
        )
      },
    )

    socket.addEventListener(
      'close',
      () => {
        if (this.socket === socket) {
          this.socket = null
        }

        this.stopHeartbeat()

        this.setStatus(
          'disconnected',
        )

        if (!this.manuallyStopped) {
          this.scheduleReconnect()
        }
      },
    )

    socket.addEventListener(
      'error',
      () => {
        socket.close()
      },
    )
  }

  disconnect() {
    this.manuallyStopped = true
    this.stopHeartbeat()

    if (
      this.reconnectTimer !== null
    ) {
      window.clearTimeout(
        this.reconnectTimer,
      )
      this.reconnectTimer = null
    }

    const socket = this.socket
    this.socket = null

    if (socket) {
      socket.close()
    }

    this.setStatus(
      'disconnected',
    )
  }

  getStatus():
  RealtimeStatus {
    return this.status
  }

  onStatus(
    handler: StatusHandler,
  ): () => void {
    this.statusHandlers.add(
      handler,
    )

    handler(this.status)

    return () => {
      this.statusHandlers.delete(
        handler,
      )
    }
  }

  onEvent<Payload = unknown>(
    type: string,
    handler:
      RealtimeEventHandler<Payload>,
  ): () => void {
    const handlers =
      this.eventHandlers.get(type)
      ?? new Set<
        RealtimeEventHandler
      >()

    handlers.add(
      handler as RealtimeEventHandler,
    )

    this.eventHandlers.set(
      type,
      handlers,
    )

    return () => {
      handlers.delete(
        handler as RealtimeEventHandler,
      )

      if (handlers.size === 0) {
        this.eventHandlers.delete(
          type,
        )
      }
    }
  }

  subscribeConversation(
    conversationType:
      ConversationType,
    conversationId: number,
  ): string {
    return this.sendCommand(
      'conversation.subscribe',
      {
        conversation_type:
          conversationType,
        conversation_id:
          conversationId,
      },
    )
  }

  unsubscribeConversation(
    conversationType:
      ConversationType,
    conversationId: number,
  ): string {
    return this.sendCommand(
      'conversation.unsubscribe',
      {
        conversation_type:
          conversationType,
        conversation_id:
          conversationId,
      },
    )
  }

  acknowledgeDelivered(
    messageId: number,
  ): string {
    return this.sendCommand(
      'message.delivered',
      {
        message_id: messageId,
      },
    )
  }

  markReadThrough(
    messageId: number,
  ): string {
    return this.sendCommand(
      'message.read',
      {
        message_id: messageId,
      },
    )
  }

  startTyping(
    conversationType:
      ConversationType,
    conversationId: number,
  ): string {
    return this.sendCommand(
      'typing.start',
      {
        conversation_type:
          conversationType,
        conversation_id:
          conversationId,
      },
    )
  }

  stopTyping(
    conversationType:
      ConversationType,
    conversationId: number,
  ): string {
    return this.sendCommand(
      'typing.stop',
      {
        conversation_type:
          conversationType,
        conversation_id:
          conversationId,
      },
    )
  }

  private startHeartbeat() {
    this.stopHeartbeat()

    const heartbeat = () => {
      if (
        this.getStatus()
        !== 'connected'
      ) {
        return
      }

      this.sendCommand(
        'presence.heartbeat',
        {},
      )
    }

    heartbeat()

    this.heartbeatTimer =
      window.setInterval(
        heartbeat,
        25000,
      )
  }

  private stopHeartbeat() {
    if (
      this.heartbeatTimer === null
    ) {
      return
    }

    window.clearInterval(
      this.heartbeatTimer,
    )
    this.heartbeatTimer = null
  }

  private sendCommand(
    type: string,
    payload:
      Record<string, unknown>,
  ): string {
    if (
      !this.socket ||
      this.socket.readyState !==
        WebSocket.OPEN
    ) {
      throw new Error(
        'Realtime connection is not open.',
      )
    }

    const requestId =
      createRequestId()

    this.socket.send(
      JSON.stringify({
        type,
        request_id:
          requestId,
        payload,
      }),
    )

    return requestId
  }

  private handleMessage(
    raw: unknown,
  ) {
    if (typeof raw !== 'string') {
      return
    }

    let event: RealtimeEvent

    try {
      event =
        JSON.parse(raw)
    } catch {
      return
    }

    if (
      !event ||
      typeof event.type !== 'string' ||
      typeof event.event_id !==
        'string'
    ) {
      return
    }

    if (
      this.seenEventIds.has(
        event.event_id,
      )
    ) {
      return
    }

    this.rememberEvent(
      event.event_id,
    )

    const handlers =
      this.eventHandlers.get(
        event.type,
      )

    if (!handlers) {
      return
    }

    for (
      const handler
      of handlers
    ) {
      handler(event)
    }
  }

  private rememberEvent(
    eventId: string,
  ) {
    this.seenEventIds.add(
      eventId,
    )

    this.seenEventOrder.push(
      eventId,
    )

    const maxRemembered = 500

    if (
      this.seenEventOrder.length >
      maxRemembered
    ) {
      const oldest =
        this.seenEventOrder.shift()

      if (oldest) {
        this.seenEventIds.delete(
          oldest,
        )
      }
    }
  }

  private setStatus(
    status: RealtimeStatus,
  ) {
    if (this.status === status) {
      return
    }

    this.status = status

    for (
      const handler
      of this.statusHandlers
    ) {
      handler(status)
    }
  }

  private scheduleReconnect() {
    if (
      this.reconnectTimer !== null
    ) {
      return
    }

    const delays = [
      1000,
      2000,
      5000,
      10000,
    ]

    const delay =
      delays[
        Math.min(
          this.reconnectAttempt,
          delays.length - 1,
        )
      ]

    this.reconnectAttempt += 1

    this.reconnectTimer =
      window.setTimeout(
        () => {
          this.reconnectTimer = null

          if (
            !this.manuallyStopped
          ) {
            this.connect()
          }
        },
        delay,
      )
  }
}
