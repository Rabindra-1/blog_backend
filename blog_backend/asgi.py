"""
ASGI config for blog_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_backend.settings')
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import chat_assistant.routing

application = ProtocolTypeRouter({
    # HTTP requests are handled by Django's ASGI application
    "http": get_asgi_application(),
    
    # WebSocket requests are handled by Channels
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                # Chat assistant WebSocket routes
                *chat_assistant.routing.websocket_urlpatterns,
            ])
        )
    ),
})
