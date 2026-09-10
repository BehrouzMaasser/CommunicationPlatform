from rest_framework import serializers

from apps.friendships.models import (
    FriendRequest,
    Friendship,
)

from apps.accounts.api.v1.serializers import PublicUserSerializer


class SendFriendRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        min_value=1,
    )


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(
        read_only=True,
    )

    recipient = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = FriendRequest
        fields = (
            "id",
            "sender",
            "recipient",
            "created_at",
        )
        read_only_fields = fields


class FriendshipSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = (
            "id",
            "friend",
            "created_at",
        )
        read_only_fields = fields

    def get_friend(self, friendship):
        current_user = self.context["request"].user

        if friendship.user_1_id == current_user.pk:
            friend = friendship.user_2
        else:
            friend = friendship.user_1

        return PublicUserSerializer(friend).data
