from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ChatSession, ChatMessage, ChatPreferences


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for chat contexts."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender_display = serializers.CharField(source='get_sender_display', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'content', 'sender', 'sender_display', 
            'message_type', 'message_type_display', 'metadata',
            'retrieved_documents', 'processing_time', 'created_at',
            'is_helpful', 'feedback_notes'
        ]
        read_only_fields = [
            'id', 'created_at', 'processing_time', 'retrieved_documents',
            'sender_display', 'message_type_display'
        ]


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new chat messages."""
    class Meta:
        model = ChatMessage
        fields = ['content', 'message_type']
        
    def validate_content(self):
        content = self.validated_data.get('content', '').strip()
        if len(content) < 1:
            raise serializers.ValidationError("Message content cannot be empty.")
        if len(content) > 5000:
            raise serializers.ValidationError("Message content is too long (max 5000 characters).")
        return content


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions with messages."""
    user = UserSerializer(read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    context_type_display = serializers.CharField(source='get_context_type_display', read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'title', 'context_type', 'context_type_display',
            'context_metadata', 'created_at', 'updated_at', 'is_active',
            'messages', 'message_count', 'last_message'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        return ChatMessageSerializer(last_msg).data if last_msg else None


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for chat session lists."""
    user = UserSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    context_type_display = serializers.CharField(source='get_context_type_display', read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'title', 'context_type', 'context_type_display',
            'created_at', 'updated_at', 'is_active', 'message_count',
            'last_message_preview'
        ]
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message_preview(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            preview = last_msg.content[:100]
            return {
                'sender': last_msg.sender,
                'content': preview + ('...' if len(last_msg.content) > 100 else ''),
                'created_at': last_msg.created_at
            }
        return None


class ChatSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new chat sessions."""
    class Meta:
        model = ChatSession
        fields = ['title', 'context_type', 'context_metadata']
        
    def validate_title(self, value):
        if value and len(value.strip()) > 255:
            raise serializers.ValidationError("Title is too long (max 255 characters).")
        return value.strip() if value else ""


class ChatPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user chat preferences."""
    user = UserSerializer(read_only=True)
    writing_style_display = serializers.CharField(source='get_writing_style_display', read_only=True)
    response_length_display = serializers.CharField(source='get_response_length_display', read_only=True)
    
    class Meta:
        model = ChatPreferences
        fields = [
            'user', 'writing_style', 'writing_style_display',
            'response_length', 'response_length_display',
            'include_references', 'auto_suggest_topics', 'context_awareness',
            'enable_suggestions', 'proactive_assistance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class ChatPromptSerializer(serializers.Serializer):
    """Serializer for processing chat prompts with context."""
    message = serializers.CharField(max_length=5000, trim_whitespace=True)
    context_type = serializers.ChoiceField(
        choices=[
            ('blog_writing', 'Blog Writing'),
            ('content_enhancement', 'Content Enhancement'),
            ('general', 'General Chat'),
        ],
        default='blog_writing'
    )
    include_blog_context = serializers.BooleanField(default=True)
    blog_draft_content = serializers.CharField(required=False, allow_blank=True)
    target_section = serializers.CharField(required=False, allow_blank=True)  # For specific sections
    
    def validate_message(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class MessageFeedbackSerializer(serializers.Serializer):
    """Serializer for message feedback."""
    is_helpful = serializers.BooleanField()
    feedback_notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate_feedback_notes(self, value):
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Feedback notes are too long (max 1000 characters).")
        return value.strip() if value else ""
