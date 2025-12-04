from django.contrib import admin
from .models import ChatSession, ChatMessage, ChatPreferences


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'context_type', 'created_at', 'updated_at', 'is_active')
    list_filter = ('context_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-updated_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'context_type', 'is_active')
        }),
        ('Context Data', {
            'fields': ('context_metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'message_type', 'created_at', 'is_helpful', 'processing_time')
    list_filter = ('sender', 'message_type', 'is_helpful', 'created_at')
    search_fields = ('session__user__username', 'content')
    readonly_fields = ('id', 'created_at', 'processing_time')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Message Info', {
            'fields': ('id', 'session', 'sender', 'message_type', 'content')
        }),
        ('AI Response Data', {
            'fields': ('metadata', 'retrieved_documents', 'context_used', 'processing_time'),
            'classes': ('collapse',)
        }),
        ('Feedback', {
            'fields': ('is_helpful', 'feedback_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session__user')


@admin.register(ChatPreferences)
class ChatPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'writing_style', 'response_length', 'include_references', 'context_awareness')
    list_filter = ('writing_style', 'response_length', 'include_references', 'context_awareness')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('AI Behavior', {
            'fields': ('writing_style', 'response_length')
        }),
        ('Content Preferences', {
            'fields': ('include_references', 'auto_suggest_topics', 'context_awareness')
        }),
        ('Notifications', {
            'fields': ('enable_suggestions', 'proactive_assistance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
