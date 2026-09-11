from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.test import APIClient

from apps.attachments.models import MessageAttachment
from apps.conversations.services import (
    DirectConversationService,
    GroupConversationService,
)
from apps.friendships.services import FriendshipService
from apps.messaging.models import Message
from apps.messaging.services import MessageService


User = get_user_model()


class AttachmentApiTestBase(TestCase):
    PASSWORD = "Strong-Test-Password!123"

    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)

        self.media_override = override_settings(
            MEDIA_ROOT=self.temp_media.name
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

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

    def login(self, user):
        logged_in = self.client.login(
            email=user.email,
            password=self.PASSWORD,
        )
        self.assertTrue(logged_in)

    @staticmethod
    def upload(
        name="notes.txt",
        content=b"hello",
        content_type="text/plain",
    ):
        return SimpleUploadedFile(
            name,
            content,
            content_type=content_type,
        )


class AttachmentApiAuthenticationTests(AttachmentApiTestBase):

    def test_attachment_download_requires_authentication(self):
        self.login(self.alice)

        create_response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "",
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        attachment_id = (
            create_response.data["attachments"][0]["id"]
        )

        self.client.logout()

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment_id},
            )
        )

        self.assertEqual(response.status_code, 401)


class AttachmentMessageCreateApiTests(AttachmentApiTestBase):

    def test_attachment_only_direct_message_can_be_created(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="notes.txt",
                        content=b"hello world",
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "")
        self.assertEqual(
            len(response.data["attachments"]),
            1,
        )

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            message.attachments.count(),
            1,
        )

    def test_text_and_attachment_direct_message_can_be_created(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "See attached",
                "attachments": [
                    self.upload(
                        name="report.pdf",
                        content=b"pdf-data",
                        content_type="application/pdf",
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["content"],
            "See attached",
        )
        self.assertEqual(
            response.data["attachments"][0]["original_filename"],
            "report.pdf",
        )
        self.assertEqual(
            response.data["attachments"][0]["mime_type"],
            "application/pdf",
        )
        self.assertEqual(
            response.data["attachments"][0]["size_bytes"],
            len(b"pdf-data"),
        )

    def test_multiple_attachments_can_be_created(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "Two files",
                "attachments": [
                    self.upload("one.txt", b"one"),
                    self.upload("two.txt", b"two"),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            len(response.data["attachments"]),
            2,
        )

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            message.attachments.count(),
            2,
        )

    def test_json_text_only_creation_still_works(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "Text only",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["content"],
            "Text only",
        )
        self.assertEqual(
            response.data["attachments"],
            [],
        )

    def test_empty_message_without_text_or_attachments_returns_400(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "   ",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Message.objects.exists()
        )

    def test_group_member_can_create_attachment_only_message(self):
        self.login(self.bob)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        message = Message.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            message.group_conversation,
            self.group,
        )

    def test_group_outsider_cannot_create_attachment_message(self):
        self.login(self.charlie)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            Message.objects.filter(
                sender=self.charlie,
            ).exists()
        )

    def test_dm_attachment_send_is_forbidden_after_unfriending(self):
        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Message.objects.filter(
                sender=self.alice,
            ).exists()
        )

    def test_attachment_reply_in_same_context_is_created(self):
        parent = MessageService.create_text_message(
            current_user=self.alice,
            direct_conversation_id=self.dm.pk,
            content="Parent",
        )

        self.login(self.bob)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "reply_to_id": parent.pk,
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["reply_to"]["id"],
            parent.pk,
        )

    def test_cross_context_attachment_reply_returns_404(self):
        group_message = MessageService.create_text_message(
            current_user=self.alice,
            group_id=self.group.pk,
            content="Group message",
        )

        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "reply_to_id": group_message.pk,
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)

    def test_message_response_does_not_expose_storage_path(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="secret.txt",
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        attachment_data = response.data["attachments"][0]

        self.assertNotIn(
            "file",
            attachment_data,
        )
        self.assertNotIn(
            "path",
            attachment_data,
        )
        self.assertNotIn(
            "token_hash",
            attachment_data,
        )

    def test_message_response_contains_download_url(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        attachment_data = response.data["attachments"][0]

        self.assertIn(
            "download_url",
            attachment_data,
        )

        self.assertIn(
            f"/api/v1/attachments/{attachment_data['id']}/",
            attachment_data["download_url"],
        )


class AttachmentSerializationApiTests(AttachmentApiTestBase):

    def test_message_detail_includes_attachment_metadata(self):
        self.login(self.alice)

        create_response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "File",
                "attachments": [
                    self.upload(
                        name="notes.txt",
                        content=b"abc",
                    ),
                ],
            },
            format="multipart",
        )

        message_id = create_response.data["id"]

        response = self.client.get(
            reverse(
                "message-detail",
                kwargs={"message_id": message_id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["attachments"][0]["original_filename"],
            "notes.txt",
        )

    def test_message_list_includes_attachment_metadata(self):
        self.login(self.alice)

        create_response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="notes.txt",
                    ),
                ],
            },
            format="multipart",
        )

        response = self.client.get(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        item = response.data["results"][0]

        self.assertEqual(
            item["id"],
            create_response.data["id"],
        )
        self.assertEqual(
            item["attachments"][0]["original_filename"],
            "notes.txt",
        )

    def test_reply_preview_includes_attachment_metadata(self):
        self.login(self.alice)

        parent_response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="parent.txt",
                    ),
                ],
            },
            format="multipart",
        )

        parent_id = parent_response.data["id"]

        reply_response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "content": "Reply",
                "reply_to_id": parent_id,
            },
            format="json",
        )

        self.assertEqual(reply_response.status_code, 201)
        self.assertEqual(
            reply_response.data["reply_to"]["attachments"][0][
                "original_filename"
            ],
            "parent.txt",
        )


class AttachmentDownloadApiTests(AttachmentApiTestBase):

    def create_dm_attachment(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "dm-message-list-create",
                kwargs={"conversation_id": self.dm.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="notes.txt",
                        content=b"download-me",
                        content_type="text/plain",
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        return MessageAttachment.objects.get(
            pk=response.data["attachments"][0]["id"]
        )

    def create_group_attachment(self):
        self.login(self.alice)

        response = self.client.post(
            reverse(
                "group-message-list-create",
                kwargs={"group_id": self.group.pk},
            ),
            {
                "attachments": [
                    self.upload(
                        name="group.txt",
                        content=b"group-download",
                        content_type="text/plain",
                    ),
                ],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

        return MessageAttachment.objects.get(
            pk=response.data["attachments"][0]["id"]
        )

    def test_dm_participant_can_download_attachment(self):
        attachment = self.create_dm_attachment()

        self.client.logout()
        self.login(self.bob)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/plain",
        )
        self.assertIn(
            'filename="notes.txt"',
            response["Content-Disposition"],
        )

        body = b"".join(response.streaming_content)

        self.assertEqual(
            body,
            b"download-me",
        )

    def test_dm_outsider_gets_404_for_attachment(self):
        attachment = self.create_dm_attachment()

        self.client.logout()
        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_dm_attachment_remains_downloadable_after_unfriending(self):
        attachment = self.create_dm_attachment()

        FriendshipService.remove_friendship(
            current_user=self.alice,
            friend_user_id=self.bob.pk,
        )

        self.client.logout()
        self.login(self.bob)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_group_member_can_download_attachment(self):
        attachment = self.create_group_attachment()

        self.client.logout()
        self.login(self.bob)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_group_outsider_gets_404_for_attachment(self):
        attachment = self.create_group_attachment()

        self.client.logout()
        self.login(self.charlie)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_former_group_member_gets_404_for_attachment(self):
        attachment = self.create_group_attachment()

        GroupConversationService.remove_member(
            current_user=self.alice,
            group_id=self.group.pk,
            member_user_id=self.bob.pk,
        )

        self.client.logout()
        self.login(self.bob)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": attachment.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_attachment_returns_404(self):
        self.login(self.alice)

        response = self.client.get(
            reverse(
                "attachment-download",
                kwargs={"attachment_id": 999999},
            )
        )

        self.assertEqual(response.status_code, 404)
