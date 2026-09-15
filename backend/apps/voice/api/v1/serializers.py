from rest_framework import serializers

from apps.accounts.api.v1.serializers import PublicUserSerializer
from apps.voice.models import (
    VoiceParticipation,
    VoiceRoom,
    VoiceRoomMembership,
    VoiceSession,
)


class ClientInstanceSerializer(serializers.Serializer):
    client_instance_id = serializers.UUIDField()


class DirectCallStartSerializer(ClientInstanceSerializer):
    user_id = serializers.IntegerField(min_value=1)


class VoiceSessionSerializer(serializers.ModelSerializer):
    caller = PublicUserSerializer(read_only=True)
    recipient = PublicUserSerializer(read_only=True)
    group_id = serializers.SerializerMethodField()

    class Meta:
        model = VoiceSession
        fields = (
            "id",
            "kind",
            "status",
            "caller",
            "recipient",
            "group_id",
            "created_at",
            "ring_expires_at",
            "activated_at",
            "ended_at",
            "end_reason",
        )
        read_only_fields = fields

    def get_group_id(self, session: VoiceSession) -> int | None:
        return session.group_id


class VoiceParticipationSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)

    class Meta:
        model = VoiceParticipation
        fields = (
            "id",
            "user",
            "role",
            "created_at",
        )
        read_only_fields = fields


class CurrentVoiceParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceParticipation
        fields = (
            "id",
            "role",
            "client_instance_id",
            "claimed_at",
            "created_at",
        )
        read_only_fields = fields


class VoiceMediaCredentialsSerializer(serializers.Serializer):
    server_url = serializers.CharField(read_only=True)
    participant_token = serializers.CharField(read_only=True)



class VoiceRoomNameSerializer(
    serializers.Serializer
):
    name = serializers.CharField(
        max_length=50,
        allow_blank=False,
        trim_whitespace=True,
    )


class VoiceRoomSerializer(
    serializers.ModelSerializer
):
    owner = PublicUserSerializer(
        read_only=True,
    )

    member_count = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = VoiceRoom
        fields = (
            "id",
            "name",
            "owner",
            "member_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_member_count(
        self,
        room: VoiceRoom,
    ) -> int:
        annotated_count = getattr(
            room,
            "member_count",
            None,
        )

        if annotated_count is not None:
            return annotated_count

        return room.memberships.count()


class VoiceRoomMembershipSerializer(
    serializers.ModelSerializer
):
    user = PublicUserSerializer(
        read_only=True,
    )

    class Meta:
        model = VoiceRoomMembership
        fields = (
            "id",
            "user",
            "joined_at",
        )
        read_only_fields = fields
