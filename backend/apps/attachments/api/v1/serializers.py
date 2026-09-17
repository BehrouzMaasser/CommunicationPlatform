from django.urls import reverse
from rest_framework import serializers

from apps.attachments.models import MessageAttachment


class MessageAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = (
            "id",
            "original_filename",
            "mime_type",
            "size_bytes",
            "created_at",
            "download_url",
        )
        read_only_fields = fields

    def get_download_url(self, attachment):
        path = reverse(
            "attachment-download",
            kwargs={
                "attachment_id": attachment.pk,
            },
        )

        return path
