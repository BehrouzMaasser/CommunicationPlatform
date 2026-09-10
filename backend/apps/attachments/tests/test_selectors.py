from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.selectors import MessageAttachmentSelector
from apps.attachments.services import MessageAttachmentService
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService

User = get_user_model()


class MessageAttachmentSelectorTests(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

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

        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        self.dm, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        self.group = GroupConversationService.create_group(
            current_user=self.alice,
            name="Study Group",
        )
        GroupConversationService._add_member(
            group=self.group,
            user=self.bob,
        )

    def upload(self, name="notes.txt"):
        return SimpleUploadedFile(
            name,
            b"hello",
            content_type="text/plain",
        )

    def test_list_for_message_returns_only_its_attachments(self):
        first_message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload("one.txt"), self.upload("two.txt")],
        )

        second_message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.bob,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload("other.txt")],
        )

        attachments = list(
            MessageAttachmentSelector.list_for_message(
                message=first_message,
            )
        )

        self.assertEqual(len(attachments), 2)
        self.assertTrue(
            all(a.message_id == first_message.pk for a in attachments)
        )
        self.assertFalse(
            any(a.message_id == second_message.pk for a in attachments)
        )

    def test_dm_participant_can_get_attachment(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        result = MessageAttachmentSelector.get_for_user(
            user=self.bob,
            attachment_id=attachment.pk,
        )

        self.assertEqual(result, attachment)

    def test_dm_outsider_cannot_get_attachment(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        result = MessageAttachmentSelector.get_for_user(
            user=self.charlie,
            attachment_id=attachment.pk,
        )

        self.assertIsNone(result)

    def test_dm_attachment_remains_accessible_after_unfriending(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        result = MessageAttachmentSelector.get_for_user(
            user=self.bob,
            attachment_id=attachment.pk,
        )

        self.assertEqual(result, attachment)

    def test_group_member_can_get_attachment(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            group_id=self.group.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        result = MessageAttachmentSelector.get_for_user(
            user=self.bob,
            attachment_id=attachment.pk,
        )

        self.assertEqual(result, attachment)

    def test_group_outsider_cannot_get_attachment(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            group_id=self.group.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        result = MessageAttachmentSelector.get_for_user(
            user=self.charlie,
            attachment_id=attachment.pk,
        )

        self.assertIsNone(result)

    def test_former_group_member_cannot_get_attachment(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            group_id=self.group.pk,
            content="",
            files=[self.upload()],
        )
        attachment = message.attachments.get()

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        result = MessageAttachmentSelector.get_for_user(
            user=self.bob,
            attachment_id=attachment.pk,
        )

        self.assertIsNone(result)

    def test_unknown_attachment_returns_none(self):
        result = MessageAttachmentSelector.get_for_user(
            user=self.alice,
            attachment_id=999999,
        )
        self.assertIsNone(result)
