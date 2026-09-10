from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService


User = get_user_model()


class ConversationsApiTestBase(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.client = APIClient()

        self.alice = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password=self.PASSWORD,
        )
        self.bob = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password=self.PASSWORD,
        )
        self.charlie = User.objects.create_user(
            email="charlie@example.com",
            username="charlie",
            password=self.PASSWORD,
        )

    def login(self, user):
        logged_in = self.client.login(
            email=user.email,
            password=self.PASSWORD,
        )
        self.assertTrue(logged_in)

    def make_friends(self, user_a, user_b):
        return FriendshipService._create_friendship(
            user_a=user_a,
            user_b=user_b,
        )


class ConversationsApiAuthenticationTests(ConversationsApiTestBase):

    def test_conversation_endpoints_require_authentication(self):
        endpoints = [
            ("get", reverse("dm-list-create"), None),
            ("post", reverse("dm-list-create"), {"user_id": self.bob.pk}),
            (
                "get",
                reverse("dm-detail", kwargs={"conversation_id": 999999}),
                None,
            ),
            ("get", reverse("group-list-create"), None),
            ("post", reverse("group-list-create"), {"name": "Study Group"}),
            (
                "get",
                reverse("group-detail", kwargs={"group_id": 999999}),
                None,
            ),
            (
                "patch",
                reverse("group-rename", kwargs={"group_id": 999999}),
                {"name": "Renamed"},
            ),
            (
                "post",
                reverse("group-leave", kwargs={"group_id": 999999}),
                None,
            ),
            (
                "get",
                reverse("group-member-list", kwargs={"group_id": 999999}),
                None,
            ),
            (
                "delete",
                reverse(
                    "group-member-delete",
                    kwargs={"group_id": 999999, "user_id": self.bob.pk},
                ),
                None,
            ),
            (
                "delete",
                reverse("group-detail", kwargs={"group_id": 999999}),
                None,
            ),
        ]

        for method, url, data in endpoints:
            with self.subTest(method=method, url=url):
                request_method = getattr(self.client, method)

                if data is None:
                    response = request_method(url)
                else:
                    response = request_method(url, data=data, format="json")

                self.assertEqual(response.status_code, 401)


class DirectConversationApiTests(ConversationsApiTestBase):

    def test_friends_can_create_direct_conversation(self):
        self.make_friends(self.alice, self.bob)
        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(DirectConversation.objects.count(), 1)

        conversation = DirectConversation.objects.get()

        self.assertEqual(
            conversation.user_1_id,
            min(self.alice.pk, self.bob.pk),
        )
        self.assertEqual(
            conversation.user_2_id,
            max(self.alice.pk, self.bob.pk),
        )

    def test_existing_direct_conversation_returns_200(self):
        self.make_friends(self.alice, self.bob)

        conversation, created = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )
        self.assertTrue(created)

        self.login(self.bob)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.alice.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], conversation.pk)
        self.assertEqual(DirectConversation.objects.count(), 1)

    def test_existing_direct_conversation_survives_unfriending(self):
        self.make_friends(self.alice, self.bob)

        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], conversation.pk)
        self.assertEqual(DirectConversation.objects.count(), 1)

    def test_new_direct_conversation_requires_friendship(self):
        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(DirectConversation.objects.exists())

    def test_direct_conversation_with_self_returns_400(self):
        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.alice.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_direct_conversation_with_unknown_user_returns_404(self):
        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_direct_conversation_response_uses_public_user_representation(self):
        self.make_friends(self.alice, self.bob)
        self.login(self.alice)

        response = self.client.post(
            reverse("dm-list-create"),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["other_user"]["id"], self.bob.pk)
        self.assertEqual(response.data["other_user"]["username"], "bob")
        self.assertNotIn("email", response.data["other_user"])

    def test_direct_conversation_list_is_paginated_and_scoped_to_user(self):
        self.make_friends(self.alice, self.bob)
        self.make_friends(self.alice, self.charlie)
        self.make_friends(self.bob, self.charlie)

        alice_bob, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )
        alice_charlie, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.charlie.pk,
        )
        DirectConversationService.get_or_create(
            current_user=self.bob,
            target_user_id=self.charlie.pk,
        )

        self.login(self.alice)

        response = self.client.get(reverse("dm-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("results", response.data)

        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertEqual(
            returned_ids,
            {alice_bob.pk, alice_charlie.pk},
        )

    def test_direct_conversation_detail_is_accessible_to_participant(self):
        self.make_friends(self.alice, self.bob)

        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "dm-detail",
                kwargs={"conversation_id": conversation.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], conversation.pk)
        self.assertEqual(response.data["other_user"]["id"], self.alice.pk)

    def test_direct_conversation_detail_returns_404_for_non_participant(self):
        self.make_friends(self.alice, self.bob)

        conversation, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "dm-detail",
                kwargs={"conversation_id": conversation.pk},
            )
        )

        self.assertEqual(response.status_code, 404)


class GroupConversationApiTests(ConversationsApiTestBase):

    def test_user_can_create_group_and_becomes_owner(self):
        self.login(self.alice)

        response = self.client.post(
            reverse("group-list-create"),
            {"name": "Study Group"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        group = GroupConversation.objects.get(pk=response.data["id"])

        membership = GroupMembership.objects.get(
            group=group,
            user=self.alice,
        )

        self.assertEqual(
            membership.role,
            GroupMembership.Role.OWNER,
        )

    def test_group_creation_with_blank_name_returns_400(self):
        self.login(self.alice)

        response = self.client.post(
            reverse("group-list-create"),
            {"name": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(GroupConversation.objects.exists())

    def test_group_list_is_paginated_and_scoped_to_memberships(self):
        alice_group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Alice Group",
        )

        bob_group = GroupConversationService.create_group(
            current_user=self.bob,
            name="Bob Group",
        )

        GroupConversationService._add_member(
            group=bob_group,
            user=self.alice,
        )

        GroupConversationService.create_group(
            current_user=self.charlie,
            name="Charlie Group",
        )

        self.login(self.alice)

        response = self.client.get(reverse("group-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertEqual(
            returned_ids,
            {alice_group.pk, bob_group.pk},
        )

    def test_group_detail_is_accessible_to_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse(
                "group-detail",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], group.pk)

    def test_group_detail_returns_404_for_non_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "group-detail",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_rename_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Old Name",
        )

        self.login(self.alice)

        response = self.client.patch(
            reverse(
                "group-rename",
                kwargs={"group_id": group.pk},
            ),
            {"name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "New Name")

        group.refresh_from_db()
        self.assertEqual(group.name, "New Name")

    def test_non_owner_member_cannot_rename_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.bob)

        response = self.client.patch(
            reverse(
                "group-rename",
                kwargs={"group_id": group.pk},
            ),
            {"name": "Unauthorized Rename"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_outsider_rename_returns_404(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.charlie)

        response = self.client.patch(
            reverse(
                "group-rename",
                kwargs={"group_id": group.pk},
            ),
            {"name": "Unauthorized Rename"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_group_member_list_is_paginated_and_does_not_expose_email(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.alice)

        response = self.client.get(
            reverse(
                "group-member-list",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        for membership in response.data["results"]:
            self.assertNotIn("email", membership["user"])

    def test_outsider_cannot_list_group_members(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "group-member-list",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_remove_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-member-delete",
                kwargs={"group_id": group.pk, "user_id": self.bob.pk},
            )
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            GroupMembership.objects.filter(
                group=group,
                user=self.bob,
            ).exists()
        )

    def test_non_owner_member_cannot_remove_another_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )
        GroupConversationService._add_member(
            group=group,
            user=self.charlie,
        )

        self.login(self.bob)

        response = self.client.delete(
            reverse(
                "group-member-delete",
                kwargs={"group_id": group.pk, "user_id": self.charlie.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            GroupMembership.objects.filter(
                group=group,
                user=self.charlie,
            ).exists()
        )

    def test_owner_cannot_remove_self_as_regular_member(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-member-delete",
                kwargs={"group_id": group.pk, "user_id": self.alice.pk},
            )
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )

    def test_regular_member_can_leave_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-leave",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            GroupMembership.objects.filter(
                group=group,
                user=self.bob,
            ).exists()
        )
        self.assertTrue(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )

    def test_owner_leaving_disbands_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-leave",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )

    def test_owner_can_disband_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-detail",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )

    def test_non_owner_member_cannot_disband_group(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        GroupConversationService._add_member(
            group=group,
            user=self.bob,
        )

        self.login(self.bob)

        response = self.client.delete(
            reverse(
                "group-detail",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )

    def test_outsider_disband_returns_404(self):
        group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )

        self.login(self.charlie)

        response = self.client.delete(
            reverse(
                "group-detail",
                kwargs={"group_id": group.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            GroupConversation.objects.filter(pk=group.pk).exists()
        )
