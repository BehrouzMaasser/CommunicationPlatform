export type GroupEventPayload = {
  group_id: number
}

export type GroupMemberEventPayload =
  GroupEventPayload & {
    user_id: number
  }

export type GroupRenamedPayload =
  GroupEventPayload & {
    name: string
  }

export type GroupInvitationEventPayload =
  GroupEventPayload & {
    invitation_id: number
    invited_by_id: number
    recipient_id: number
  }

export type GroupInvitationAcceptedEventPayload =
  GroupInvitationEventPayload & {
    group_name: string
    recipient_username: string
  }
