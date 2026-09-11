class MessagingError(Exception):
    """Base exception for expected messaging-domain failures."""

    code = "messaging_error"
    default_message = "A messaging domain error occurred."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidMessageContext(MessagingError):
    code = "invalid_message_context"
    default_message = "A message must belong to exactly one messaging context."


class MessageContextNotFound(MessagingError):
    code = "message_context_not_found"
    default_message = "The messaging context does not exist or is not accessible."


class InvalidMessageContent(MessagingError):
    code = "invalid_message_content"
    default_message = "A text message must contain non-empty text content."


class ReplyMessageNotFound(MessagingError):
    code = "reply_message_not_found"
    default_message = "The reply target does not exist in this messaging context."


class MessageNotFound(MessagingError):
    code = "message_not_found"
    default_message = "The message does not exist or is not accessible."


class FriendshipRequiredForDirectMessage(MessagingError):
    code = "friendship_required_for_direct_message"
    default_message = "Users must be friends to send direct messages."
