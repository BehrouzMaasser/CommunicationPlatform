from django.urls import path

from apps.activity.api.v1.views import ActivitySummaryView


urlpatterns = [
    path(
        "activity/summary/",
        ActivitySummaryView.as_view(),
        name="activity-summary",
    ),
]
