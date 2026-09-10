from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from tempfile import TemporaryDirectory

from apps.attachments.models import MessageAttachment
from apps.conversations.services import DirectConversationService
from apps.friendships.services import FriendshipService
from apps.messaging.services import MessageService

User = get_user_model()


class MessageAttachmentModelTests(TestCase):
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

        FriendshipService._create_friendship(
            user_a=self.alice,
            user_b=self.bob,
        )

        self.dm, _ = DirectConversationService.get_or_create(
            current_user=self.alice,
            target_user_id=self.bob.pk,
        )

        self.message = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="Hello",
        )

    def test_attachment_metadata_is_persisted(self):
        upload = SimpleUploadedFile(
            "notes.txt",
            b"hello world",
            content_type="text/plain",
        )

        attachment = MessageAttachment.objects.create(
            message=self.message,
            file=upload,
            original_filename="notes.txt",
            mime_type="text/plain",
            size_bytes=11,
        )

        self.assertEqual(attachment.message, self.message)
        self.assertEqual(attachment.original_filename, "notes.txt")
        self.assertEqual(attachment.mime_type, "text/plain")
        self.assertEqual(attachment.size_bytes, 11)

    def test_storage_path_does_not_use_original_filename(self):
        upload = SimpleUploadedFile(
            "secret-name.txt",
            b"hello",
            content_type="text/plain",
        )

        attachment = MessageAttachment.objects.create(
            message=self.message,
            file=upload,
            original_filename="secret-name.txt",
            mime_type="text/plain",
            size_bytes=5,
        )

        self.assertNotIn("secret-name.txt", attachment.file.name)
        self.assertIn(
            f"message_attachments/{self.message.pk}/",
            attachment.file.name,
        )

    def test_attachment_row_is_deleted_with_message(self):
        upload = SimpleUploadedFile(
            "notes.txt",
            b"hello",
            content_type="text/plain",
        )

        attachment = MessageAttachment.objects.create(
            message=self.message,
            file=upload,
            original_filename="notes.txt",
            mime_type="text/plain",
            size_bytes=5,
        )

        attachment_id = attachment.pk
        self.message.delete()

        self.assertFalse(
            MessageAttachment.objects.filter(pk=attachment_id).exists()
        )
