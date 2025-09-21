# accounts/ws_auth.py
import jwt
from django.conf import settings
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Get User model dynamically
        User = get_user_model()

        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get('headers', []))
        token = None
        auth = headers.get('authorization')
        if auth and auth.lower().startswith('bearer '):
            token = auth.split(' ', 1)[1]
        else:
            qs = parse_qs(scope.get('query_string', b'').decode())
            token = qs.get('token', [None])[0]

        if token:
            try:
                data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                user_id = data.get('sub')
                user = await database_sync_to_async(User.objects.get)(id=user_id)
                scope['user'] = user
            except Exception:
                scope['user'] = None
        else:
            scope['user'] = None

        return await self.app(scope, receive, send)