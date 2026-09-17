from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.avatar_urls import build_avatar_url


User = get_user_model()


class PublicUserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "avatar_url",
        )
        read_only_fields = fields

    def get_avatar_url(self, user):
        return build_avatar_url(
            user_id=user.pk,
            avatar_name=(
                user.avatar.name
                if user.avatar
                else None
            ),
        )


class CurrentUserSerializer(PublicUserSerializer):

    class Meta(PublicUserSerializer.Meta):
        fields = (
            *PublicUserSerializer.Meta.fields,
            "email",
        )
        read_only_fields = fields


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField(
        allow_empty_file=False,
    )
