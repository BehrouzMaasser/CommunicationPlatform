import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import (
    TransactionTestCase,
    override_settings,
)

from apps.attachments.services import (
    MessageAttachmentService,
)
from apps.conversations.models import (
    DirectConversation,
    GroupConversation,
    GroupMembership,
)
from apps.friendships.models import Friendship
from apps.messaging.services import MessageService


User = get_user_model()


class MessageCreatedRealtimeTests(
    TransactionTestCase
):

    reset_sequences = True

    def setUp(self):
        self.alice = (
            User.objects.create_user(
                username="alice",
                email="alice@example.com",
                password="password-123",
            )
        )

        self.bob = (
            User.objects.create_user(
                username="bob",
                email="bob@example.com",
                password="password-123",
            )
        )

        Friendship.objects.create(
            user_1=self.alice,
            user_2=self.bob,
        )

        self.dm = (
            DirectConversation.objects.create(
                user_1=self.alice,
                user_2=self.bob,
            )
        )

        self.group = (
            GroupConversation.objects.create(
                name="Study Group",
            )
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.alice,
            role=(
                GroupMembership
                .Role
                .OWNER
            ),
        )

        GroupMembership.objects.create(
            group=self.group,
            user=self.bob,
            role=(
                GroupMembership
                .Role
                .MEMBER
            ),
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher.publish"
    )
    def test_text_dm_publishes_message_created(
        self,
        publish,
    ):
        message = (
            MessageService
            .create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="Hello Bob",
            )
        )

        publish.assert_called_once()

        kwargs = (
            publish.call_args.kwargs
        )

        self.assertEqual(
            kwargs["event_type"].value,
            "message.created",
        )

        self.assertCountEqual(
            kwargs["group_names"],
            [
                f"dm.{self.dm.pk}",
                f"user.{self.alice.pk}",
                f"user.{self.bob.pk}",
            ],
        )

        payload = kwargs["payload"]

        self.assertEqual(
            payload[
                "conversation_type"
            ],
            "dm",
        )
        self.assertEqual(
            payload[
                "conversation_id"
            ],
            self.dm.pk,
        )
        self.assertEqual(
            payload["message"]["id"],
            message.pk,
        )
        self.assertEqual(
            payload[
                "message"
            ]["content"],
            "Hello Bob",
        )
        self.assertEqual(
            payload[
                "message"
            ]["sender"],
            {
                "id": self.alice.pk,
                "username": "alice",
            },
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher.publish"
    )
    def test_group_message_targets_group_channel(
        self,
        publish,
    ):
        message = (
            MessageService
            .create_text_message(
                current_user=self.bob,
                group_id=self.group.pk,
                content="Hello group",
            )
        )

        kwargs = (
            publish.call_args.kwargs
        )

        self.assertCountEqual(
            kwargs["group_names"],
            [
                f"group.{self.group.pk}",
                f"user.{self.alice.pk}",
                f"user.{self.bob.pk}",
            ],
        )
        self.assertEqual(
            kwargs["payload"][
                "conversation_type"
            ],
            "group",
        )
        self.assertEqual(
            kwargs["payload"][
                "message"
            ]["id"],
            message.pk,
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher.publish"
    )
    def test_reply_payload_contains_shallow_reply(
        self,
        publish,
    ):
        original = (
            MessageService
            .create_text_message(
                current_user=self.alice,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="Original",
            )
        )

        publish.reset_mock()

        reply = (
            MessageService
            .create_text_message(
                current_user=self.bob,
                direct_conversation_id=(
                    self.dm.pk
                ),
                content="Reply",
                reply_to_id=original.pk,
            )
        )

        payload = (
            publish
            .call_args
            .kwargs["payload"]
        )

        self.assertEqual(
            payload["message"]["id"],
            reply.pk,
        )
        self.assertEqual(
            payload[
                "message"
            ]["reply_to"]["id"],
            original.pk,
        )
        self.assertEqual(
            payload[
                "message"
            ]["reply_to"]["content"],
            "Original",
        )

    @patch(
        "apps.messaging.realtime."
        "RealtimePublisher.publish"
    )
    def test_attachment_event_is_published_after_files_exist(
        self,
        publish,
    ):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(
                MEDIA_ROOT=media_root
            ):
                message = (
                    MessageAttachmentService
                    .create_message_with_attachments(
                        current_user=self.alice,
                        direct_conversation_id=(
                            self.dm.pk
                        ),
                        content="With file",
                        files=[
                            SimpleUploadedFile(
                                "notes.txt",
                                b"hello",
                                content_type=(
                                    "text/plain"
                                ),
                            )
                        ],
                    )
                )

        publish.assert_called_once()

        payload = (
            publish
            .call_args
            .kwargs["payload"]
        )

        attachments = (
            payload[
                "message"
            ]["attachments"]
        )

        self.assertEqual(
            payload["message"]["id"],
            message.pk,
        )
        self.assertEqual(
            len(attachments),
            1,
        )
        self.assertEqual(
            attachments[0][
                "original_filename"
            ],
            "notes.txt",
        )
        self.assertEqual(
            attachments[0][
                "mime_type"
            ],
            "text/plain",
        )
        self.assertTrue(
            attachments[0][
                "download_url"
            ].endswith(
                f"/api/v1/attachments/"
                f"{attachments[0]['id']}/"
            )
        )
