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



export type MessageDeliveredPayload = {
  conversation_type:
    'dm' | 'group'
  conversation_id: number
  message_id: number
  user_id: number
  delivered_at: string
}


export type MessageReadPayload = {
  conversation_type:
    'dm' | 'group'
  conversation_id: number
  message_id: number
  user_id: number
  read_at: string
  read_count: number
}
