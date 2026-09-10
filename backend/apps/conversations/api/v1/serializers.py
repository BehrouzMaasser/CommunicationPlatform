from rest_framework import serializers

from apps.accounts.api.v1.serializers import PublicUserSerializer
from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)


class DirectConversationCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        min_value=1,
    )


class DirectConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = DirectConversation
        fields = (
            "id",
            "other_user",
            "created_at",
            "last_activity_at",
        )
        read_only_fields = fields

    def get_other_user(self, conversation):
        current_user = self.context["request"].user

        if conversation.user_1_id == current_user.pk:
            other_user = conversation.user_2
        else:
            other_user = conversation.user_1

        return PublicUserSerializer(other_user).data


class GroupNameSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=25,
        allow_blank=True,
        trim_whitespace=False,
    )


class GroupConversationSerializer(serializers.ModelSerializer):

    class Meta:
        model = GroupConversation
        fields = (
            "id",
            "name",
            "created_at",
            "last_activity_at",
        )
        read_only_fields = fields


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = GroupMembership
        fields = (
            "user",
            "role",
            "joined_at",
        )
        read_only_fields = fields
