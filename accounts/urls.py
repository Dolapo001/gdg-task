from django.urls import path
from . import views

urlpatterns = [
    path("login", views.github_login, name="github-login"),
    path("callback", views.github_callback, name="github-callback"),
]
