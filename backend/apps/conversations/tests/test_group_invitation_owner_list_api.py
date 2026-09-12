from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.conversations.models import GroupInvitation
from apps.conversations.services import GroupConversationService
from apps.friendships.models import Friendship


User = get_user_model()


class GroupInvitationOwnerListApiTests(APITestCase):

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

        low, high = sorted(
            [self.alice, self.bob],
            key=lambda user: user.pk,
        )
        Friendship.objects.create(
            user_1=low,
            user_2=high,
        )

        self.group = (
            GroupConversationService
            .create_group(
                current_user=self.alice,
                name="Study Group",
            )
        )

    def login(self, user):
        self.client.force_authenticate(
            user=user
        )

    def test_owner_can_list_pending_group_invitations(self):
        invitation = (
            GroupInvitation.objects.create(
                group=self.group,
                invited_by=self.alice,
                recipient=self.bob,
            )
        )

        self.login(self.alice)

        response = self.client.get(
            f"/api/v1/groups/{self.group.pk}/invitations/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            invitation.pk,
        )
        self.assertEqual(
            response.data[0][
                "recipient"
            ]["id"],
            self.bob.pk,
        )

    def test_non_owner_member_cannot_list_pending_invitations(self):
        (
            GroupConversationService
            ._add_member(
                group=self.group,
                user=self.bob,
            )
        )
        self.login(self.bob)

        response = self.client.get(
            f"/api/v1/groups/{self.group.pk}/invitations/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_outsider_gets_404(self):
        self.login(self.charlie)

        response = self.client.get(
            f"/api/v1/groups/{self.group.pk}/invitations/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )
