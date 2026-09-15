from django.urls import path

from apps.voice.api.v1.views import (
    DirectCallAcceptView,
    DirectCallCancelView,
    DirectCallEndView,
    DirectCallRejectView,
    DirectCallStartView,
    GroupVoiceLeaveView,
    GroupVoiceView,
    VoiceMediaCredentialsView,
    VoiceStateView,
)


urlpatterns = [
    path(
        "voice/state/",
        VoiceStateView.as_view(),
        name="voice-state",
    ),
    path(
        "voice/direct-calls/",
        DirectCallStartView.as_view(),
        name="voice-direct-call-start",
    ),
    path(
        "voice/direct-calls/<uuid:session_id>/accept/",
        DirectCallAcceptView.as_view(),
        name="voice-direct-call-accept",
    ),
    path(
        "voice/direct-calls/<uuid:session_id>/reject/",
        DirectCallRejectView.as_view(),
        name="voice-direct-call-reject",
    ),
    path(
        "voice/direct-calls/<uuid:session_id>/cancel/",
        DirectCallCancelView.as_view(),
        name="voice-direct-call-cancel",
    ),
    path(
        "voice/direct-calls/<uuid:session_id>/end/",
        DirectCallEndView.as_view(),
        name="voice-direct-call-end",
    ),
    path(
        "voice/sessions/<uuid:session_id>/media-credentials/",
        VoiceMediaCredentialsView.as_view(),
        name="voice-media-credentials",
    ),
    path(
        "groups/<int:group_id>/voice/",
        GroupVoiceView.as_view(),
        name="group-voice",
    ),
    path(
        "groups/<int:group_id>/voice/leave/",
        GroupVoiceLeaveView.as_view(),
        name="group-voice-leave",
    ),
]
