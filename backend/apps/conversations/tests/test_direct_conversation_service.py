from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.exceptions import (
    DirectConversationTargetNotFound,
    FriendshipRequiredForDirectConversation,
    SelfDirectConversationNotAllowed,
)
from apps.conversations.models import DirectConversation
from apps.conversations.services.direct_conversation import (
    DirectConversationService,
)
from apps.friendships.services.friendship import FriendshipService


User = get_user_model()


class DirectConversationServiceTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
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

    def test_friends_can_create_direct_conversation(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        conversation, created = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        self.assertTrue(created)

        self.assertEqual(
            DirectConversation.objects.count(),
            1,
        )

        self.assertEqual(
            conversation.user_1_id,
            min(self.alice.pk, self.bob.pk),
        )

        self.assertEqual(
            conversation.user_2_id,
            max(self.alice.pk, self.bob.pk),
        )

    def test_direct_conversation_is_reused(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        first_conversation, first_created = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        second_conversation, second_created = (
            DirectConversationService.get_or_create(
                current_user=self.bob,
                target_user_id=self.alice.pk,
            )
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_conversation,
            second_conversation,
        )

        self.assertEqual(
            DirectConversation.objects.count(),
            1,
        )

    def test_new_direct_conversation_requires_friendship(self):
        with self.assertRaises(
            FriendshipRequiredForDirectConversation
        ):
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )

        self.assertFalse(
            DirectConversation.objects.exists()
        )

    def test_existing_direct_conversation_survives_unfriending(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        conversation, created = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        self.assertTrue(created)

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        reused_conversation, reused_created = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        self.assertFalse(reused_created)

        self.assertEqual(
            reused_conversation,
            conversation,
        )

        self.assertEqual(
            DirectConversation.objects.count(),
            1,
        )

    def test_existing_direct_conversation_can_be_reused_by_either_participant_after_unfriending(
        self,
    ):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        conversation, _ = (
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
        )

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        reused_conversation, created = (
            DirectConversationService.get_or_create(
                current_user=self.bob,
                target_user_id=self.alice.pk,
            )
        )

        self.assertFalse(created)
        self.assertEqual(
            reused_conversation,
            conversation,
        )

    def test_user_cannot_create_direct_conversation_with_self(self):
        with self.assertRaises(
            SelfDirectConversationNotAllowed
        ):
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.alice.pk,
            )

        self.assertFalse(
            DirectConversation.objects.exists()
        )

    def test_unknown_target_user_raises(self):
        with self.assertRaises(
            DirectConversationTargetNotFound
        ):
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=999999,
            )

    def test_friendship_with_unrelated_user_does_not_allow_conversation(self):
        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.charlie,
        )

        with self.assertRaises(
            FriendshipRequiredForDirectConversation
        ):
            DirectConversationService.get_or_create(
                current_user=self.alice,
                target_user_id=self.bob.pk,
            )
