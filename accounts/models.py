from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    github_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    avatar_url = models.URLField(null=True, blank=True)

class OAuthState(models.Model):
    """Stores OAuth 'state' tokens for CSRF protection. Short TTL."""
    state = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    next_url = models.CharField(max_length=512, blank=True, null=True)

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() > 300
