from django.urls import path, include
from django.contrib import admin
from accounts.views import me

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/github/", include("accounts.urls")),
    path("me/", me, name="me"),
    path("", include("chat.urls")),
]
