from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from apps.conversations.models import (
    GroupConversation,
    GroupInvitation,
    GroupInvitationLink,
    GroupMembership,
)
from apps.conversations.services import (
    GroupConversationService,
    GroupInvitationLinkService,
    GroupInvitationService,
)
from apps.friendships.services import FriendshipService


User = get_user_model()


class GroupInvitationApiTestBase(TestCase):
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

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
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


class GroupInvitationApiAuthenticationTests(
    GroupInvitationApiTestBase
):

    def test_invitation_endpoints_require_authentication(self):
        endpoints = [
            (
                "post",
                reverse(
                    "group-invitation-create",
                    kwargs={"group_id": self.group.pk},
                ),
                {"user_id": self.bob.pk},
            ),
            (
                "get",
                reverse("group-invitation-list"),
                None,
            ),
            (
                "post",
                reverse(
                    "group-invitation-accept",
                    kwargs={"invitation_id": 999999},
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "group-invitation-reject",
                    kwargs={"invitation_id": 999999},
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "group-invitation-link-create",
                    kwargs={"group_id": self.group.pk},
                ),
                None,
            ),
            (
                "delete",
                reverse(
                    "group-invitation-link-revoke",
                    kwargs={
                        "group_id": self.group.pk,
                        "link_id": 999999,
                    },
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "group-invitation-link-join",
                    kwargs={"token": "example-token"},
                ),
                None,
            ),
        ]

        for method, url, data in endpoints:
            with self.subTest(method=method, url=url):
                request_method = getattr(self.client, method)

                if data is None:
                    response = request_method(url)
                else:
                    response = request_method(
                        url,
                        data=data,
                        format="json",
                    )

                self.assertEqual(response.status_code, 401)


class DirectGroupInvitationApiTests(
    GroupInvitationApiTestBase
):

    def test_owner_can_invite_friend(self):
        self.make_friends(self.alice, self.bob)
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        invitation = GroupInvitation.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(invitation.group, self.group)
        self.assertEqual(invitation.invited_by, self.alice)
        self.assertEqual(invitation.recipient, self.bob)

    def test_invitation_response_does_not_expose_email(self):
        self.make_friends(self.alice, self.bob)
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertNotIn(
            "email",
            response.data["invited_by"],
        )
        self.assertNotIn(
            "email",
            response.data["recipient"],
        )

    def test_non_owner_member_cannot_invite(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        self.make_friends(self.bob, self.charlie)
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.charlie.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            GroupInvitation.objects.filter(
                recipient=self.charlie,
            ).exists()
        )

    def test_outsider_invite_returns_404(self):
        self.make_friends(self.charlie, self.bob)
        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_cannot_invite_non_friend(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            GroupInvitation.objects.exists()
        )

    def test_owner_cannot_invite_existing_member(self):
        self.make_friends(self.alice, self.bob)

        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_duplicate_pending_invitation_returns_409(self):
        self.make_friends(self.alice, self.bob)

        GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": self.bob.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            GroupInvitation.objects.filter(
                group=self.group,
                recipient=self.bob,
            ).count(),
            1,
        )

    def test_unknown_target_user_returns_404(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-create",
                kwargs={"group_id": self.group.pk},
            ),
            {"user_id": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_incoming_invitation_list_is_paginated_and_scoped(self):
        self.make_friends(self.alice, self.bob)
        self.make_friends(self.alice, self.charlie)

        bob_invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.charlie.pk,
        )

        self.login(self.bob)

        response = self.client.get(
            reverse("group-invitation-list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            bob_invitation.pk,
        )

        self.assertNotIn(
            "email",
            response.data["results"][0]["invited_by"],
        )
        self.assertNotIn(
            "email",
            response.data["results"][0]["recipient"],
        )

    def test_recipient_can_accept_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-accept",
                kwargs={"invitation_id": invitation.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

        self.assertNotIn(
            "email",
            response.data["user"],
        )

    def test_non_recipient_accept_returns_404(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-invitation-accept",
                kwargs={"invitation_id": invitation.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

    def test_unknown_invitation_accept_returns_404(self):
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-accept",
                kwargs={"invitation_id": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_recipient_can_reject_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-reject",
                kwargs={"invitation_id": invitation.pk},
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

    def test_non_recipient_reject_returns_404(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-invitation-reject",
                kwargs={"invitation_id": invitation.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )


class GroupInvitationLinkApiTests(
    GroupInvitationApiTestBase
):

    def test_owner_can_create_invitation_link(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-invitation-link-create",
                kwargs={"group_id": self.group.pk},
            )
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertIn("token", response.data)
        self.assertIn("created_at", response.data)
        self.assertIn("expires_at", response.data)
        self.assertNotIn("token_hash", response.data)

        link = GroupInvitationLink.objects.get(
            pk=response.data["id"]
        )

        self.assertNotEqual(
            link.token_hash,
            response.data["token"],
        )

        self.assertEqual(
            link.token_hash,
            GroupInvitationLinkService._hash_token(
                response.data["token"]
            ),
        )

    def test_non_owner_member_cannot_create_link(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-create",
                kwargs={"group_id": self.group.pk},
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            GroupInvitationLink.objects.exists()
        )

    def test_outsider_link_creation_returns_404(self):
        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-invitation-link-create",
                kwargs={"group_id": self.group.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_valid_link_allows_non_friend_to_join(self):
        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": token},
            )
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

        self.assertNotIn(
            "email",
            response.data["user"],
        )

    def test_existing_member_join_returns_200(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": token},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).count(),
            1,
        )

    def test_invalid_link_returns_400(self):
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": "invalid-token"},
            )
        )

        self.assertEqual(response.status_code, 400)

    def test_expired_link_returns_400(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        GroupInvitationLink.objects.filter(
            pk=link.pk,
        ).update(
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": token},
            )
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            GroupMembership.objects.filter(
                group=self.group,
                user=self.bob,
            ).exists()
        )

    def test_revoked_link_returns_400(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        GroupInvitationLinkService.revoke_link(
            current_user=self.alice,
            group_id=self.group.pk,
            link_id=link.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": token},
            )
        )

        self.assertEqual(response.status_code, 400)

    def test_link_join_removes_redundant_direct_invitation(self):
        self.make_friends(self.alice, self.bob)

        invitation = GroupInvitationService.create_invitation(
            current_user=self.alice,
            group_id=self.group.pk,
            target_user_id=self.bob.pk,
        )

        _, token = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-invitation-link-join",
                kwargs={"token": token},
            )
        )

        self.assertEqual(response.status_code, 201)

        self.assertFalse(
            GroupInvitation.objects.filter(
                pk=invitation.pk,
            ).exists()
        )

    def test_owner_can_revoke_link(self):
        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-invitation-link-revoke",
                kwargs={
                    "group_id": self.group.pk,
                    "link_id": link.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 204)

        link.refresh_from_db()
        self.assertIsNotNone(link.revoked_at)

    def test_non_owner_member_cannot_revoke_link(self):
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.bob)

        response = self.client.delete(
            reverse(
                "group-invitation-link-revoke",
                kwargs={
                    "group_id": self.group.pk,
                    "link_id": link.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 403)

        link.refresh_from_db()
        self.assertIsNone(link.revoked_at)

    def test_outsider_revoke_returns_404(self):
        link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=self.group.pk,
        )

        self.login(self.charlie)

        response = self.client.delete(
            reverse(
                "group-invitation-link-revoke",
                kwargs={
                    "group_id": self.group.pk,
                    "link_id": link.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_link_revoke_returns_404(self):
        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-invitation-link-revoke",
                kwargs={
                    "group_id": self.group.pk,
                    "link_id": 999999,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_link_from_another_group_cannot_be_revoked_through_this_group(self):
        other_group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Other Group",
        )

        other_link, _ = GroupInvitationLinkService.create_link(
            current_user=self.alice,
            group_id=other_group.pk,
        )

        self.login(self.alice)

        response = self.client.delete(
            reverse(
                "group-invitation-link-revoke",
                kwargs={
                    "group_id": self.group.pk,
                    "link_id": other_link.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

        other_link.refresh_from_db()
        self.assertIsNone(other_link.revoked_at)
