import io
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase


User = get_user_model()


def make_image_upload(
    *,
    name="avatar.png",
    image_format="PNG",
    size=(80, 60),
):
    output = io.BytesIO()
    image = Image.new(
        "RGB",
        size,
        (120, 80, 200),
    )
    image.save(
        output,
        format=image_format,
    )

    return SimpleUploadedFile(
        name,
        output.getvalue(),
        content_type={
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "WEBP": "image/webp",
        }[image_format],
    )


class UserAvatarApiTests(APITestCase):

    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.override_media = override_settings(
            MEDIA_ROOT=self.temp_media.name,
        )
        self.override_media.enable()

        self.user = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="Strong-Test-Password!123",
        )
        self.other_user = User.objects.create_user(
            email="bob@example.com",
            username="bob",
            password="Strong-Test-Password!123",
        )
        self.client.force_login(self.user)

    def tearDown(self):
        self.override_media.disable()
        self.temp_media.cleanup()

    def test_current_user_has_null_avatar_url_by_default(self):
        response = self.client.get(
            reverse("api-current-user"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIsNone(
            response.data["avatar_url"],
        )

    def test_user_can_upload_avatar_and_receive_versioned_url(self):
        response = self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name)
        self.assertTrue(
            self.user.avatar.name.endswith(".webp")
        )

        avatar_url = response.data["avatar_url"]
        self.assertTrue(
            avatar_url.startswith(
                reverse(
                    "api-user-avatar",
                    kwargs={
                        "user_id": self.user.pk,
                    },
                )
            )
        )
        self.assertIn("?v=", avatar_url)

    def test_avatar_endpoint_returns_normalized_webp(self):
        self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(
                    size=(120, 80),
                ),
            },
            format="multipart",
        )

        response = self.client.get(
            reverse(
                "api-user-avatar",
                kwargs={
                    "user_id": self.user.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response["Content-Type"],
            "image/webp",
        )

        payload = b"".join(
            response.streaming_content
        )
        with Image.open(
            io.BytesIO(payload)
        ) as image:
            self.assertEqual(
                image.format,
                "WEBP",
            )
            self.assertEqual(
                image.size,
                (512, 512),
            )

    def test_authenticated_user_can_read_another_users_avatar(self):
        self.client.force_login(self.other_user)
        self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "api-user-avatar",
                kwargs={
                    "user_id": self.other_user.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_avatar_endpoint_requires_authentication(self):
        self.client.force_login(self.other_user)
        self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )

        self.client.logout()
        response = self.client.get(
            reverse(
                "api-user-avatar",
                kwargs={
                    "user_id": self.other_user.pk,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_invalid_image_payload_is_rejected(self):
        fake_image = SimpleUploadedFile(
            "avatar.png",
            b"not actually an image",
            content_type="image/png",
        )

        response = self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": fake_image,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertIn(
            "detail",
            response.data,
        )

    @override_settings(
        USER_AVATAR_MAX_SIZE_BYTES=10,
    )
    def test_oversized_avatar_is_rejected(self):
        response = self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_user_can_remove_avatar(self):
        self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )
        self.user.refresh_from_db()
        old_path = Path(self.user.avatar.path)
        self.assertTrue(old_path.exists())

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            response = self.client.delete(
                reverse("api-current-user-avatar"),
            )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertIsNone(
            response.data["avatar_url"],
        )

        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.avatar))
        self.assertFalse(old_path.exists())

    def test_public_user_representation_includes_avatar_url(self):
        self.client.force_login(self.other_user)
        upload_response = self.client.put(
            reverse("api-current-user-avatar"),
            {
                "avatar": make_image_upload(),
            },
            format="multipart",
        )
        expected_url = upload_response.data[
            "avatar_url"
        ]

        self.client.force_login(self.user)
        response = self.client.get(
            reverse("api-user-lookup"),
            {
                "search": "bob",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["results"][0]["avatar_url"],
            expected_url,
        )
