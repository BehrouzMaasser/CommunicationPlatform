from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.voice.models import (
    VoiceRoom,
    VoiceRoomMembership,
)
from apps.voice.services.voice_room import (
    VoiceRoomService,
)


User = get_user_model()


@override_settings(
    VOICE_ENABLED=True
)
class VoiceRoomApiTests(APITestCase):

    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.owner = User.objects.create_user(
            username="api-room-owner",
            email="api-room-owner@example.com",
            password=self.PASSWORD,
        )

        self.member = User.objects.create_user(
            username="api-room-member",
            email="api-room-member@example.com",
            password=self.PASSWORD,
        )

        self.outsider = User.objects.create_user(
            username="api-room-outsider",
            email="api-room-outsider@example.com",
            password=self.PASSWORD,
        )

        self.room = VoiceRoomService.create_room(
            current_user=self.owner,
            name="Gaming",
        )

        VoiceRoomMembership.objects.create(
            room=self.room,
            user=self.member,
        )

    def authenticate(self, user):
        self.client.force_authenticate(
            user=user
        )

    def test_user_can_create_room(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.post(
            reverse(
                "voice-room-list-create"
            ),
            {
                "name": "Study",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        room = VoiceRoom.objects.get(
            pk=response.data["id"],
        )

        self.assertEqual(
            room.owner,
            self.outsider,
        )

        self.assertTrue(
            VoiceRoomMembership.objects.filter(
                room=room,
                user=self.outsider,
            ).exists()
        )

    def test_blank_room_name_returns_400(self):
        self.authenticate(
            self.owner
        )

        response = self.client.post(
            reverse(
                "voice-room-list-create"
            ),
            {
                "name": "   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_room_list_is_paginated_and_member_scoped(self):
        other_room = (
            VoiceRoomService.create_room(
                current_user=self.member,
                name="Study",
            )
        )

        VoiceRoomService.create_room(
            current_user=self.outsider,
            name="Hidden",
        )

        self.authenticate(
            self.member
        )

        response = self.client.get(
            reverse(
                "voice-room-list-create"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        returned_ids = {
            item["id"]
            for item
            in response.data["results"]
        }

        self.assertEqual(
            returned_ids,
            {
                str(self.room.id),
                str(other_room.id),
            },
        )

    def test_member_can_get_room_detail(self):
        self.authenticate(
            self.member
        )

        response = self.client.get(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(self.room.id),
        )

    def test_outsider_gets_404_for_room_detail(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.get(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_owner_can_rename_room(self):
        self.authenticate(
            self.owner
        )

        response = self.client.patch(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "name": "New Name",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.room.refresh_from_db()

        self.assertEqual(
            self.room.name,
            "New Name",
        )

    def test_non_owner_member_cannot_rename_room(self):
        self.authenticate(
            self.member
        )

        response = self.client.patch(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "name": "Nope",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["code"],
            "VOICE_ROOM_OWNER_REQUIRED",
        )

    def test_outsider_rename_returns_404(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.patch(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            ),
            {
                "name": "Nope",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_member_can_list_room_members(self):
        self.authenticate(
            self.member
        )

        response = self.client.get(
            reverse(
                "voice-room-member-list",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_user_ids = {
            item["user"]["id"]
            for item
            in response.data["results"]
        }

        self.assertEqual(
            returned_user_ids,
            {
                self.owner.id,
                self.member.id,
            },
        )

    def test_outsider_cannot_list_room_members(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.get(
            reverse(
                "voice-room-member-list",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_member_can_leave_room(self):
        self.authenticate(
            self.member
        )

        response = self.client.delete(
            reverse(
                "voice-room-leave",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.member,
            ).exists()
        )

    def test_owner_cannot_leave_room(self):
        self.authenticate(
            self.owner
        )

        response = self.client.delete(
            reverse(
                "voice-room-leave",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        self.assertEqual(
            response.data["code"],
            "VOICE_ROOM_OWNER_CANNOT_LEAVE",
        )

    def test_owner_can_remove_member(self):
        self.authenticate(
            self.owner
        )

        response = self.client.delete(
            reverse(
                "voice-room-member-delete",
                kwargs={
                    "room_id": self.room.id,
                    "user_id": self.member.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            VoiceRoomMembership.objects.filter(
                room=self.room,
                user=self.member,
            ).exists()
        )

    def test_non_owner_cannot_remove_member(self):
        self.authenticate(
            self.member
        )

        response = self.client.delete(
            reverse(
                "voice-room-member-delete",
                kwargs={
                    "room_id": self.room.id,
                    "user_id": self.owner.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_cannot_remove_self(self):
        self.authenticate(
            self.owner
        )

        response = self.client.delete(
            reverse(
                "voice-room-member-delete",
                kwargs={
                    "room_id": self.room.id,
                    "user_id": self.owner.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        self.assertEqual(
            response.data["code"],
            "VOICE_ROOM_OWNER_CANNOT_BE_REMOVED",
        )

    def test_owner_can_delete_room(self):
        self.authenticate(
            self.owner
        )

        room_id = self.room.id

        response = self.client.delete(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": room_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            VoiceRoom.objects.filter(
                pk=room_id,
            ).exists()
        )

    def test_non_owner_member_cannot_delete_room(self):
        self.authenticate(
            self.member
        )

        response = self.client.delete(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_delete_returns_404(self):
        self.authenticate(
            self.outsider
        )

        response = self.client.delete(
            reverse(
                "voice-room-detail",
                kwargs={
                    "room_id": self.room.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )
