from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activity.selectors import ActivitySummarySelector


class ActivitySummaryView(APIView):

    def get(self, request):
        return Response(
            ActivitySummarySelector.get_for_user(
                user=request.user,
            )
        )
