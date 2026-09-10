class AttachmentsError(Exception):
    """Base exception for expected attachment-domain failures."""

    code = "attachments_error"
    default_message = "An attachment domain error occurred."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidAttachment(AttachmentsError):
    code = "invalid_attachment"
    default_message = "The attachment is invalid."


class AttachmentNotFound(AttachmentsError):
    code = "attachment_not_found"
    default_message = (
        "The attachment does not exist or is not accessible."
    )
