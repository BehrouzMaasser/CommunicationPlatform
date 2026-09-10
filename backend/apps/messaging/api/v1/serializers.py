from rest_framework import serializers

from apps.accounts.api.v1.serializers import PublicUserSerializer
from apps.messaging.models import Message


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
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

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "created_at",
        )
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(
        read_only=True,
    )
    reply_to = MessageReplySerializer(
        read_only=True,
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "reply_to",
            "created_at",
        )
        read_only_fields = fields
