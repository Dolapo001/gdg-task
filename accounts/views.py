import os
import secrets
import logging
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
import requests

from .auth import JWTAuthentication
from .models import OAuthState, User
from .serializers import UserSerializer
import jwt

logger = logging.getLogger(__name__)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

def get_env_var(name: str):
    """Helper to fetch env var safely with clear error if missing."""
    value = os.getenv(name)
    if not value:
        logger.error("Missing required environment variable: %s", name)
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

@require_GET
def github_login(request):
    """Create ephemeral state and redirect to GitHub authorize URL."""
    state = secrets.token_urlsafe(32)
    next_url = request.GET.get("next")
    OAuthState.objects.create(state=state, next_url=next_url)

    client_id = get_env_var("GITHUB_CLIENT_ID")

    params = {
        "client_id": client_id,
        "redirect_uri": request.build_absolute_uri(reverse("github-callback")),
        "scope": "read:user user:email",
        "state": state,
    }
    url = requests.Request("GET", GITHUB_AUTHORIZE_URL, params=params).prepare().url
    return redirect(url)

@require_GET
def github_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    if not code or not state:
        return HttpResponseBadRequest("Missing code or state")

    try:
        stored = OAuthState.objects.get(state=state)
    except OAuthState.DoesNotExist:
        return HttpResponseBadRequest("Invalid state")

    if stored.is_expired():
        stored.delete()
        return HttpResponseBadRequest("State expired")

    client_id = get_env_var("GITHUB_CLIENT_ID")
    client_secret = get_env_var("GITHUB_CLIENT_SECRET")

    # Exchange code for access_token
    try:
        resp = requests.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": request.build_absolute_uri(reverse("github-callback")),
                "state": state,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except requests.RequestException:
        logger.exception("Error exchanging code for token")
        return JsonResponse({"error": "token_exchange_failed"}, status=500)

    access_token = token_data.get("access_token")
    if not access_token:
        logger.warning("No access_token in GitHub response: %s", token_data)
        return JsonResponse({"error": "no_access_token"}, status=400)

    # Fetch profile
    try:
        profile_resp = requests.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    except requests.RequestException:
        logger.exception("Error fetching GitHub profile")
        return JsonResponse({"error": "profile_fetch_failed"}, status=500)

    # Create/update user
    github_id = profile.get("id")
    username = profile.get("login") or f"gh_{github_id}"
    email = profile.get("email") or ""
    avatar = profile.get("avatar_url")

    user, _ = User.objects.update_or_create(
        github_id=github_id,
        defaults={"username": username, "email": email, "avatar_url": avatar},
    )

    # Issue app JWT
    payload = {
        "sub": str(user.id),
        "iat": int(timezone.now().timestamp()),
        "exp": int((timezone.now() + timezone.timedelta(seconds=settings.JWT_EXP_SECONDS)).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    # Clean up state
    stored.delete()

    return JsonResponse({"token": token, "user": UserSerializer(user).data})


@require_GET
def me(request):
    """Return the current user profile from JWT."""
    auth = JWTAuthentication()
    user_auth = auth.authenticate(request)

    if not user_auth:
        return JsonResponse({"error": "unauthorized"}, status=401)

    user, _ = user_auth
    return JsonResponse(UserSerializer(user).data)