from django.urls import path

from apps.attachments.api.v1.views import (
    AttachmentDownloadView,
)


urlpatterns = [
    path(
        "attachments/<int:attachment_id>/",
        AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
]
