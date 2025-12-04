from django.urls import path
from . import views

app_name = 'chat_assistant'

urlpatterns = [
    # Chat sessions
    path('sessions/', views.ChatSessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<uuid:pk>/', views.ChatSessionDetailView.as_view(), name='session-detail'),
    
    # Messages
    path('sessions/<uuid:session_id>/messages/', views.ChatMessageListView.as_view(), name='message-list'),
    path('sessions/<uuid:session_id>/send/', views.send_message, name='send-message'),
    
    # Quick chat (no session persistence)
    path('quick-chat/', views.quick_chat, name='quick-chat'),
    
    # Message feedback
    path('messages/<uuid:message_id>/feedback/', views.message_feedback, name='message-feedback'),
    
    # User preferences
    path('preferences/', views.ChatPreferencesView.as_view(), name='preferences'),
    
    # Suggestions
    path('suggestions/', views.chat_suggestions, name='suggestions'),
    path('sessions/<uuid:session_id>/suggestions/', views.chat_suggestions, name='session-suggestions'),
    
    # System status
    path('status/', views.system_status, name='status'),
]
