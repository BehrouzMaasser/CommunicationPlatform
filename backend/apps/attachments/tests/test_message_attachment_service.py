from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.exceptions import InvalidAttachment
from apps.attachments.models import MessageAttachment
from apps.attachments.services import MessageAttachmentService
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService
from apps.messaging.exceptions import (
    InvalidMessageContent,
    FriendshipRequiredForDirectMessage,
    MessageContextNotFound,
    ReplyMessageNotFound,
)
from apps.messaging.models import Message
from apps.messaging.services import MessageService

User = get_user_model()


class MessageAttachmentServiceTests(TestCase):
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

    def upload(self, name="notes.txt", content=b"hello", content_type="text/plain"):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_attachment_only_message_is_allowed(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
        )

        self.assertEqual(message.content, "")
        self.assertEqual(message.attachments.count(), 1)

    def test_text_and_attachment_message_is_allowed(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="See attached",
            files=[self.upload()],
        )

        self.assertEqual(message.content, "See attached")
        self.assertEqual(message.attachments.count(), 1)

    def test_text_only_payload_is_allowed(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="Text only",
            files=[],
        )

        self.assertEqual(message.content, "Text only")
        self.assertEqual(message.attachments.count(), 0)

    def test_empty_text_and_no_attachments_is_rejected(self):
        with self.assertRaises(InvalidMessageContent):
            MessageAttachmentService.create_message_with_attachments(
                current_user=self.alice,
                direct_conversation_id=self.dm.pk,
                content="   ",
                files=[],
            )

        self.assertFalse(Message.objects.exists())

    def test_metadata_and_opaque_storage_name(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[
                self.upload(
                    name="my report.pdf",
                    content=b"pdf-data",
                    content_type="application/pdf",
                )
            ],
        )

        attachment = message.attachments.get()

        self.assertEqual(attachment.original_filename, "my report.pdf")
        self.assertEqual(attachment.mime_type, "application/pdf")
        self.assertEqual(attachment.size_bytes, len(b"pdf-data"))
        self.assertNotIn("my report.pdf", attachment.file.name)

    def test_missing_mime_type_uses_default(self):
        upload = SimpleUploadedFile("file.bin", b"abc")
        upload.content_type = None

        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[upload],
        )

        self.assertEqual(
            message.attachments.get().mime_type,
            MessageAttachmentService.DEFAULT_MIME_TYPE,
        )

    def test_group_member_can_send_attachment_message(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.bob,
            group_id=self.group.pk,
            content="",
            files=[self.upload()],
        )

        self.assertEqual(message.group_conversation, self.group)

    def test_group_outsider_cannot_send_attachment_message(self):
        with self.assertRaises(MessageContextNotFound):
            MessageAttachmentService.create_message_with_attachments(
                current_user=self.charlie,
                group_id=self.group.pk,
                content="",
                files=[self.upload()],
            )

    def test_existing_dm_blocks_new_attachment_after_unfriending(self):
        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        with self.assertRaises(FriendshipRequiredForDirectMessage):
            MessageAttachmentService.create_message_with_attachments(
                current_user=self.alice,
                direct_conversation_id=self.dm.pk,
                content="",
                files=[self.upload()],
            )

        self.assertFalse(Message.objects.exists())
        self.assertFalse(MessageAttachment.objects.exists())

    def test_same_context_reply_with_attachment_is_allowed(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="Parent",
        )

        reply = MessageAttachmentService.create_message_with_attachments(
            current_user=self.bob,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
            reply_to_id=parent.pk,
        )

        self.assertEqual(reply.reply_to, parent)

    def test_cross_context_reply_is_rejected(self):
        group_message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        with self.assertRaises(ReplyMessageNotFound):
            MessageAttachmentService.create_message_with_attachments(
                current_user=self.alice,
                direct_conversation_id=self.dm.pk,
                content="",
                files=[self.upload()],
                reply_to_id=group_message.pk,
            )

        self.assertFalse(MessageAttachment.objects.exists())

    def test_multiple_attachments_are_created(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[
                self.upload("one.txt", b"one"),
                self.upload("two.txt", b"two"),
            ],
        )

        self.assertEqual(message.attachments.count(), 2)

    def test_invalid_attachment_is_rejected_before_message_creation(self):
        upload = ContentFile(
            b"hello",
            name="x" * 256,
        )

        with self.assertRaises(InvalidAttachment):
            MessageAttachmentService.create_message_with_attachments(
                current_user=self.alice,
                direct_conversation_id=self.dm.pk,
                content="",
                files=[upload],
            )

        self.assertFalse(Message.objects.exists())

    def test_last_activity_is_updated(self):
        message = MessageAttachmentService.create_message_with_attachments(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="",
            files=[self.upload()],
        )

        self.dm.refresh_from_db()
        self.assertEqual(self.dm.last_activity_at, message.created_at)

    def test_failure_after_first_file_write_cleans_up_storage(self):
        first = self.upload("one.txt", b"one")
        second = self.upload("two.txt", b"two")

        original = MessageAttachmentService._create_attachment_record
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated failure")
            return original(*args, **kwargs)

        with patch.object(
            MessageAttachmentService,
            "_create_attachment_record",
            side_effect=fail_second,
        ):
            with self.assertRaises(RuntimeError):
                MessageAttachmentService.create_message_with_attachments(
                    current_user=self.alice,
                    direct_conversation_id=self.dm.pk,
                    content="",
                    files=[first, second],
                )

        self.assertFalse(Message.objects.exists())
        self.assertFalse(MessageAttachment.objects.exists())

        remaining_files = [
            path
            for path in Path(self.temp_media.name).rglob("*")
            if path.is_file()
        ]
        self.assertEqual(remaining_files, [])
