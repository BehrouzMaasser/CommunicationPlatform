from rest_framework import serializers

from apps.accounts.api.v1.serializers import (
    PublicUserSerializer,
)
from apps.attachments.api.v1.serializers import (
    MessageAttachmentSerializer,
)
from apps.messaging.models import Message, MessageReceipt


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        default="",
    )
    reply_to_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )


class MessageReplySerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(
        read_only=True,
    )
    attachments = MessageAttachmentSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "attachments",
            "created_at",
        )
        read_only_fields = fields


class MessageReceiptSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = MessageReceipt
        fields = (
            "user",
            "delivered_at",
            "read_at",
        )
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(
        read_only=True,
    )
    reply_to = MessageReplySerializer(
        read_only=True,
    )
    attachments = MessageAttachmentSerializer(
        many=True,
        read_only=True,
    )
    receipts = MessageReceiptSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "attachments",
            "reply_to",
            "receipts",
            "created_at",
        )
        read_only_fields = fields
