from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class CurrentUserView(LoginRequiredMixin, View):

    def get(self, request):
        return render(
            request,
            "accounts/me.html",
            {
                "user": request.user,
                "frontend_base_url": settings.FRONTEND_BASE_URL,
            }
        )
