from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from apps.conversations.models import GroupInvitationLink
from apps.conversations.services import (
    GroupConversationService,
    GroupInvitationLinkService,
)


User = get_user_model()


class GroupInvitationLinkListApiTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.client = APIClient()

        self.owner = User.objects.create_user(
            email="owner@example.com",
            username="owner",
            password=self.PASSWORD,
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            username="member",
            password=self.PASSWORD,
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            username="outsider",
            password=self.PASSWORD,
        )

        self.group = GroupConversationService.create_group(
            current_user=self.owner,
            name="Study Group",
        )
        GroupConversationService._add_member(
            group=self.group,
            user=self.member,
        )

        self.url = reverse(
            "group-invitation-link-create",
            kwargs={"group_id": self.group.pk},
        )

    def login(self, user):
        logged_in = self.client.login(
            email=user.email,
            password=self.PASSWORD,
        )
        self.assertTrue(logged_in)

    def test_owner_can_list_only_active_links(self):
        active_link, _ = (
            GroupInvitationLinkService.create_link(
                current_user=self.owner,
                group_id=self.group.pk,
            )
        )
        revoked_link, _ = (
            GroupInvitationLinkService.create_link(
                current_user=self.owner,
                group_id=self.group.pk,
            )
        )
        expired_link, _ = (
            GroupInvitationLinkService.create_link(
                current_user=self.owner,
                group_id=self.group.pk,
            )
        )

        GroupInvitationLinkService.revoke_link(
            current_user=self.owner,
            group_id=self.group.pk,
            link_id=revoked_link.pk,
        )
        GroupInvitationLink.objects.filter(
            pk=expired_link.pk,
        ).update(
            expires_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        self.login(self.owner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data],
            [active_link.pk],
        )

    def test_owner_list_returns_recoverable_token_but_never_token_hash(self):
        link, token = GroupInvitationLinkService.create_link(
            current_user=self.owner,
            group_id=self.group.pk,
        )

        self.login(self.owner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], link.pk)
        self.assertEqual(response.data[0]["token"], token)
        self.assertNotIn("token_hash", response.data[0])
        self.assertNotIn(link.token_hash, str(response.data))

    def test_legacy_link_is_listed_without_recoverable_token(self):
        raw_token = GroupInvitationLinkService._generate_token()
        link = GroupInvitationLink.objects.create(
            group=self.group,
            created_by=self.owner,
            token_hash=(
                GroupInvitationLinkService._hash_token(
                    raw_token
                )
            ),
            expires_at=(
                timezone.now()
                + timedelta(hours=1)
            ),
        )

        self.login(self.owner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], link.pk)
        self.assertIsNone(response.data[0]["token"])
        self.assertNotIn("token_hash", response.data[0])

    def test_non_owner_member_cannot_list_links(self):
        self.login(self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_discover_group_links(self):
        self.login(self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_list_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
