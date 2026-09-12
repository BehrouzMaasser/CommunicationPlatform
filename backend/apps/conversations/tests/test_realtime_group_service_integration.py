from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.conversations.models import (
    GroupConversation,
    GroupMembership,
)
from apps.conversations.services import (
    GroupConversationService,
)


User = get_user_model()


class GroupRealtimeServiceIntegrationTests(APITestCase):
    """
    Real HTTP -> real service -> real GroupRealtimePublisher.
    Mock only the lower transport boundary.
    """

    PUBLISH = (
        "apps.conversations.realtime."
        "RealtimePublisher.publish_after_commit"
    )
    FORCE = (
        "apps.conversations.realtime."
        "RealtimePublisher."
        "force_unsubscribe_user_from_conversation_after_commit"
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
        self.charlie = User.objects.create_user(
            username="charlie",
            email="charlie@example.com",
            password="password-123",
        )

    def login(self, user):
        self.client.force_authenticate(user=user)

    def create_group(self):
        return GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

    @patch(PUBLISH)
    def test_rename_reaches_real_adapter(self, publish):
        group = self.create_group()
        self.login(self.alice)

        response = self.client.patch(
            f"/api/v1/groups/{group.pk}/rename/",
            {"name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any(
                call.kwargs["event_type"].value
                == "group.renamed"
                for call in publish.call_args_list
            )
        )

    @patch(FORCE)
    @patch(PUBLISH)
    def test_remove_member_publishes_and_revokes(
        self,
        publish,
        force,
    ):
        group = self.create_group()
        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )
        self.login(self.alice)

        response = self.client.delete(
            f"/api/v1/groups/{group.pk}/members/{self.bob.pk}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            any(
                call.kwargs["event_type"].value
                == "group.member_removed"
                for call in publish.call_args_list
            )
        )
        force.assert_called_once_with(
            user_id=self.bob.pk,
            conversation_type="group",
            conversation_id=group.pk,
        )

    @patch(FORCE)
    @patch(PUBLISH)
    def test_member_leave_publishes_and_revokes(
        self,
        publish,
        force,
    ):
        group = self.create_group()
        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )
        self.login(self.bob)

        response = self.client.post(
            f"/api/v1/groups/{group.pk}/leave/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            any(
                call.kwargs["event_type"].value
                == "group.member_left"
                for call in publish.call_args_list
            )
        )
        force.assert_called_once_with(
            user_id=self.bob.pk,
            conversation_type="group",
            conversation_id=group.pk,
        )

    @patch(FORCE)
    @patch(PUBLISH)
    def test_disband_publishes_deleted_and_revokes_all(
        self,
        publish,
        force,
    ):
        group = self.create_group()
        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )
        group_id = group.pk

        self.login(self.alice)

        response = self.client.delete(
            f"/api/v1/groups/{group_id}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            GroupConversation.objects.filter(
                pk=group_id,
            ).exists()
        )
        self.assertTrue(
            any(
                call.kwargs["event_type"].value
                == "group.deleted"
                for call in publish.call_args_list
            )
        )

        forced_ids = {
            call.kwargs["user_id"]
            for call in force.call_args_list
        }
        self.assertEqual(
            forced_ids,
            {
                self.alice.pk,
                self.bob.pk,
            },
        )

    @patch(PUBLISH)
    def test_owner_leave_is_group_deleted_not_member_left(
        self,
        publish,
    ):
        group = self.create_group()
        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )
        group_id = group.pk
        self.login(self.alice)

        response = self.client.post(
            f"/api/v1/groups/{group_id}/leave/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 204)

        event_types = [
            call.kwargs["event_type"].value
            for call in publish.call_args_list
        ]

        self.assertIn(
            "group.deleted",
            event_types,
        )
        self.assertNotIn(
            "group.member_left",
            event_types,
        )
