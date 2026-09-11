import type { PublicUser } from './users'

export type MessageAttachment = {
  id: number
  original_filename: string
  mime_type: string
  size_bytes: number
  created_at: string
  download_url: string
}

export type MessageReply = {
  id: number
  sender: PublicUser
  content: string
  attachments: MessageAttachment[]
  created_at: string
}

export type Message = {
  id: number
  sender: PublicUser
  content: string
  attachments: MessageAttachment[]
  reply_to: MessageReply | null
  created_at: string
}

export type PaginatedMessages = {
  count: number
  next: string | null
  previous: string | null
  results: Message[]
}
