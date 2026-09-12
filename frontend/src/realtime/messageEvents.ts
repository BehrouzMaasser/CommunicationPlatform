import type {
  Message,
} from '../types/messages'
import type {
  ConversationType,
} from './types'


export type MessageCreatedPayload = {
  conversation_type:
    ConversationType
  conversation_id: number
  message: Message
}
