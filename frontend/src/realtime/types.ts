export type RealtimeStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'


export type ConversationType =
  | 'dm'
  | 'group'


export type RealtimeEvent<
  Payload = unknown,
> = {
  type: string
  event_id: string
  timestamp: string
  payload: Payload
  request_id?: string
}


export type RealtimeEventHandler<
  Payload = unknown,
> = (
  event: RealtimeEvent<Payload>,
) => void
