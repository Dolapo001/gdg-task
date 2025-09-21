# ASGI middleware to authenticate WebSocket connections using app JWT
import jwt
from django.conf import settings
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from .models import User


class JWTAuthMiddleware:
    """Simple ASGI middleware factory that reads 'Authorization' header or ?token= and
    attaches `scope['user']`.
    """
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JWTAuthMiddlewareInstance(scope, self.inner)


class JWTAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        headers = dict((k.decode().lower(), v.decode()) for k, v in self.scope.get('headers', []))
        token = None
        auth = headers.get('authorization')
        if auth and auth.lower().startswith('bearer '):
            token = auth.split(' ', 1)[1]
        else:
            # try query_string
            qs = parse_qs(self.scope.get('query_string', b'').decode())
            token = qs.get('token', [None])[0]

        if token:
            try:
                data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                user_id = data.get('sub')
                user = await database_sync_to_async(User.objects.get)(id=user_id)
                self.scope['user'] = user
            except Exception:
                # leave user as AnonymousUser (or reject on consumer side)
                self.scope['user'] = None
        else:
            self.scope['user'] = None

        inner = self.inner(self.scope)
        return await inner(receive, send)
