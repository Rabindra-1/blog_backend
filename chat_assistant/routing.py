from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket route for persistent chat sessions
    re_path(r'ws/chat/(?P<session_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    
    # WebSocket route for quick chat (no persistent session)
    re_path(r'ws/quick-chat/$', consumers.QuickChatConsumer.as_asgi()),
]
