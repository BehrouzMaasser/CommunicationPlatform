from rest_framework import serializers

from apps.accounts.models import User


class PublicUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            "id",
            "username",
        )
        read_only_fields = fields
