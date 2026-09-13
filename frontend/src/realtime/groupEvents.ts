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

export const groupLifecycleEventTypes = [
  'group_invitation.created',
  'group_invitation.accepted',
  'group_invitation.rejected',
  'group.member_added',
  'group.member_removed',
  'group.member_left',
  'group.renamed',
  'group.deleted',
] as const
