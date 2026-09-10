class ConversationsError(Exception):
    """Base exception for expected conversation-domain failures."""

    code = "conversations_error"
    default_message = "A conversation domain error occurred."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class DirectConversationTargetNotFound(ConversationsError):
    code = "direct_conversation_target_not_found"
    default_message = "The target user does not exist."


class SelfDirectConversationNotAllowed(ConversationsError):
    code = "self_direct_conversation_not_allowed"
    default_message = "A user cannot start a direct conversation with themselves."


class FriendshipRequiredForDirectConversation(ConversationsError):
    code = "friendship_required_for_direct_conversation"
    default_message = "Users must be friends to start a direct conversation."


class GroupNotFound(ConversationsError):
    code = "group_not_found"
    default_message = "The group does not exist."


class GroupMembershipNotFound(ConversationsError):
    code = "group_membership_not_found"
    default_message = "The user is not a member of this group."


class GroupOwnerRequired(ConversationsError):
    code = "group_owner_required"
    default_message = "Only the group owner may perform this operation."


class UserAlreadyGroupMember(ConversationsError):
    code = "user_already_group_member"
    default_message = "The user is already a member of this group."


class GroupOwnerCannotBeRemoved(ConversationsError):
    code = "group_owner_cannot_be_removed"
    default_message = "The group owner cannot be removed as a regular member."


class InvalidGroupName(ConversationsError):
    code = "invalid_group_name"
    default_message = "The group name must not be empty."
