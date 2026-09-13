from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.conversations.models import GroupMembership
from apps.conversations.services import GroupConversationService
from apps.friendships.models import Friendship


User = get_user_model()


class GroupInvitationRealtimeIntegrationTests(APITestCase):
    PUBLISH = (
        "apps.conversations.realtime."
        "RealtimePublisher.publish_after_commit"
    )

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password-123",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password-123",
        )

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )
        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

    def login(self, user):
        self.client.force_authenticate(user=user)

    @patch(PUBLISH)
    def test_create_invitation_publishes_created(self, publish):
        self.login(self.alice)

        response = self.client.post(
            f"/api/v1/groups/{self.group.pk}/invitations/",
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            publish.call_args.kwargs["event_type"].value,
            "group_invitation.created",
        )

    @patch(PUBLISH)
    def test_accept_publishes_accept_and_member_added(self, publish):
        self.login(self.alice)
        created = self.client.post(
            f"/api/v1/groups/{self.group.pk}/invitations/",
            {"user_id": self.bob.pk},
            format="json",
        )
        invitation_id = created.data["id"]

        publish.reset_mock()
        self.login(self.bob)

        response = self.client.post(
            f"/api/v1/group-invitations/{invitation_id}/accept/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        event_types = {
            call.kwargs["event_type"].value
            for call in publish.call_args_list
        }
        self.assertEqual(
            event_types,
            {
                "group_invitation.accepted",
                "group.member_added",
            },
        )

        accepted_call = next(
            call
            for call in publish.call_args_list
            if (
                call.kwargs["event_type"].value
                == "group_invitation.accepted"
            )
        )
        self.assertEqual(
            accepted_call.kwargs["payload"]["group_name"],
            "Study Group",
        )
        self.assertEqual(
            accepted_call.kwargs["payload"]["recipient_username"],
            "bob",
        )
        self.assertTrue(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

    @patch(PUBLISH)
    def test_reject_publishes_rejected(self, publish):
        self.login(self.alice)
        created = self.client.post(
            f"/api/v1/groups/{self.group.pk}/invitations/",
            {"user_id": self.bob.pk},
            format="json",
        )
        invitation_id = created.data["id"]

        publish.reset_mock()
        self.login(self.bob)

        response = self.client.post(
            f"/api/v1/group-invitations/{invitation_id}/reject/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            publish.call_args.kwargs["event_type"].value,
            "group_invitation.rejected",
        )
