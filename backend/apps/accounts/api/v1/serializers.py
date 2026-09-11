from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class PublicUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            "id",
            "username",
        )
        read_only_fields = fields


class CurrentUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
        )
        read_only_fields = fields
