from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ChatSession(models.Model):
    """Represents a chat session between user and AI assistant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)  # Auto-generated from first message
    context_type = models.CharField(
        max_length=50, 
        choices=[
            ('blog_writing', 'Blog Writing'),
            ('general', 'General Chat'),
            ('content_enhancement', 'Content Enhancement'),
        ],
        default='blog_writing'
    )
    context_metadata = models.JSONField(default=dict, blank=True)  # Store blog ID, draft content, etc.
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'context_type']),
        ]

    def __str__(self):
        return f"Chat Session {self.id} - {self.user.username}"

    def save(self, *args, **kwargs):
        # Auto-generate title from first message if not set
        if not self.title and self.pk:
            first_message = self.messages.filter(sender='user').first()
            if first_message:
                self.title = first_message.content[:50] + ('...' if len(first_message.content) > 50 else '')
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """Individual messages within a chat session."""
    SENDER_CHOICES = [
        ('user', 'User'),
        ('assistant', 'AI Assistant'),
        ('system', 'System'),
    ]

    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('suggestion', 'Content Suggestion'),
        ('generation', 'Generated Content'),
        ('enhancement', 'Content Enhancement'),
        ('system', 'System Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    
    # Metadata for AI responses
    metadata = models.JSONField(default=dict, blank=True)  # Store tokens used, model info, etc.
    
    # RAG context information
    retrieved_documents = models.JSONField(default=list, blank=True)  # Store retrieved document refs
    context_used = models.TextField(blank=True)  # Store the context that was used for generation
    
    # Response timing
    processing_time = models.FloatField(null=True, blank=True)  # Time taken to generate response
    
    created_at = models.DateTimeField(default=timezone.now)
    
    # Feedback system
    is_helpful = models.BooleanField(null=True, blank=True)  # User feedback
    feedback_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['sender', 'message_type']),
        ]

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}..."


class ChatPreferences(models.Model):
    """User preferences for chat assistant behavior."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_preferences')
    
    # AI behavior preferences
    writing_style = models.CharField(
        max_length=50,
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('creative', 'Creative'),
            ('academic', 'Academic'),
        ],
        default='professional'
    )
    
    response_length = models.CharField(
        max_length=20,
        choices=[
            ('short', 'Short & Concise'),
            ('medium', 'Medium'),
            ('long', 'Detailed'),
        ],
        default='medium'
    )
    
    # Content preferences
    include_references = models.BooleanField(default=True)
    auto_suggest_topics = models.BooleanField(default=True)
    context_awareness = models.BooleanField(default=True)  # Use blog history for context
    
    # Notification preferences
    enable_suggestions = models.BooleanField(default=True)
    proactive_assistance = models.BooleanField(default=False)  # AI suggests improvements
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat Preferences - {self.user.username}"
