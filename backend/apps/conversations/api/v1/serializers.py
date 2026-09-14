from rest_framework import serializers

from apps.accounts.api.v1.serializers import PublicUserSerializer
from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupInvitation,
    GroupInvitationLink,
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


class GroupInvitationCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        min_value=1,
    )


class GroupInvitationSerializer(serializers.ModelSerializer):
    group = GroupConversationSerializer(
        read_only=True,
    )
    invited_by = PublicUserSerializer(
        read_only=True,
    )
    recipient = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = GroupInvitation
        fields = (
            "id",
            "group",
            "invited_by",
            "recipient",
            "created_at",
        )
        read_only_fields = fields


class GroupInvitationLinkSummarySerializer(
    serializers.ModelSerializer
):
    created_by = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = GroupInvitationLink
        fields = (
            "id",
            "created_by",
            "created_at",
            "expires_at",
        )
        read_only_fields = fields


class GroupInvitationLinkCreateResponseSerializer(
    serializers.Serializer
):
    id = serializers.IntegerField(
        read_only=True,
    )
    token = serializers.CharField(
        read_only=True,
    )
    created_at = serializers.DateTimeField(
        read_only=True,
    )
    expires_at = serializers.DateTimeField(
        read_only=True,
    )
