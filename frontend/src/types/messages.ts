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

export type MessageReceipt = {
  user: PublicUser
  delivered_at: string | null
  read_at: string | null
}

export type Message = {
  id: number
  sender: PublicUser
  content: string
  attachments: MessageAttachment[]
  reply_to: MessageReply | null
  receipts: MessageReceipt[]
  created_at: string
}

export type MessageDraft = {
  content: string
  replyToId?: number
  files?: File[]
}
