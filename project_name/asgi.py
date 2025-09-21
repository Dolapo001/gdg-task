# project_name/asgi.py
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Set Django settings module first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_name.settings")

# Configure Django before any imports
django.setup()

# Now import your components that depend on Django
from chat.routing import websocket_urlpatterns
from accounts.ws_auth import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})