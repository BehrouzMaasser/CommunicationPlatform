from django.http import FileResponse
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.attachments.selectors import (
    MessageAttachmentSelector,
)


class AttachmentDownloadView(APIView):

    def get(self, request, attachment_id):
        attachment = (
            MessageAttachmentSelector.get_for_user(
                user=request.user,
                attachment_id=attachment_id,
            )
        )

        if attachment is None:
            raise NotFound

        attachment.file.open("rb")

        return FileResponse(
            attachment.file,
            as_attachment=True,
            filename=attachment.original_filename,
            content_type=attachment.mime_type,
        )
