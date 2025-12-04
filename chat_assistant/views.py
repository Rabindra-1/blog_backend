from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
import logging

from .models import ChatSession, ChatMessage, ChatPreferences
from .serializers import (
    ChatSessionSerializer, ChatSessionListSerializer, ChatSessionCreateSerializer,
    ChatMessageSerializer, ChatMessageCreateSerializer, ChatPreferencesSerializer,
    ChatPromptSerializer, MessageFeedbackSerializer
)
# Always use SimpleChatService for now since the complex service has dependency issues
from .simple_service import SimpleChatService as ChatAssistantService

logger = logging.getLogger(__name__)


class ChatSessionListCreateView(generics.ListCreateAPIView):
    """List user's chat sessions or create a new one."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChatSessionCreateSerializer
        return ChatSessionListSerializer
    
    def get_queryset(self):
        return ChatSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-updated_at')
    
    def perform_create(self, serializer):
        # Create session using the service
        service = ChatAssistantService()
        session = service.create_chat_session(
            user=self.request.user,
            context_type=serializer.validated_data.get('context_type', 'blog_writing'),
            context_metadata=serializer.validated_data.get('context_metadata', {})
        )
        
        # Update title if provided
        if serializer.validated_data.get('title'):
            session.title = serializer.validated_data['title']
            session.save()
        
        return session


class ChatSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific chat session."""
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete by setting is_active to False
        instance.is_active = False
        instance.save()


class ChatMessageListView(generics.ListAPIView):
    """List messages for a specific chat session."""
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        session_id = self.kwargs.get('session_id')
        session = get_object_or_404(
            ChatSession, 
            id=session_id, 
            user=self.request.user
        )
        return session.messages.all().order_by('created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, session_id):
    """Send a message in a chat session and get AI response."""
    try:
        # Get the session
        session = get_object_or_404(
            ChatSession, 
            id=session_id, 
            user=request.user,
            is_active=True
        )
        
        # Validate the message
        message_serializer = ChatMessageCreateSerializer(data=request.data)
        if not message_serializer.is_valid():
            return Response(
                message_serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_message = message_serializer.validated_data['content']
        
        # Get context data from request
        context_data = {
            'blog_draft_content': request.data.get('blog_draft_content', ''),
            'target_section': request.data.get('target_section', ''),
            'include_blog_context': request.data.get('include_blog_context', True)
        }
        
        # Process the message using the service
        service = ChatAssistantService()
        ai_response = service.process_message(
            session=session,
            user_message=user_message,
            context_data=context_data
        )
        
        # Return the AI response
        response_data = ChatMessageSerializer(ai_response).data
        
        # Add suggestions if requested
        if request.data.get('include_suggestions', False):
            suggestions = service.get_chat_suggestions(session)
            response_data['suggestions'] = suggestions
        
        return Response({
            'message': response_data,
            'session_updated': True
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        return Response({
            'error': 'An error occurred while processing your message.',
            'detail': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_chat(request):
    """Send a quick message without creating a persistent session."""
    try:
        # Validate the prompt
        prompt_serializer = ChatPromptSerializer(data=request.data)
        if not prompt_serializer.is_valid():
            return Response(
                prompt_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = prompt_serializer.validated_data
        user_message = validated_data['message']
        
        # Create a temporary session
        service = ChatAssistantService()
        temp_session = service.create_chat_session(
            user=request.user,
            context_type=validated_data['context_type'],
            context_metadata={'temporary': True}
        )
        
        # Process the message
        context_data = {
            'blog_draft_content': validated_data.get('blog_draft_content', ''),
            'target_section': validated_data.get('target_section', ''),
            'include_blog_context': validated_data.get('include_blog_context', True)
        }
        
        ai_response = service.process_message(
            session=temp_session,
            user_message=user_message,
            context_data=context_data
        )
        
        # Return just the response without persisting the session
        response_data = ChatMessageSerializer(ai_response).data
        
        # Clean up temporary session if requested
        if request.data.get('cleanup_session', True):
            temp_session.delete()
        
        return Response({
            'response': response_data,
            'session_id': temp_session.id if not request.data.get('cleanup_session', True) else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in quick_chat: {str(e)}")
        return Response({
            'error': 'An error occurred while processing your request.',
            'detail': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_feedback(request, message_id):
    """Provide feedback on an AI message."""
    try:
        # Validate feedback data
        feedback_serializer = MessageFeedbackSerializer(data=request.data)
        if not feedback_serializer.is_valid():
            return Response(
                feedback_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = feedback_serializer.validated_data
        
        # Provide feedback using the service
        service = ChatAssistantService()
        success = service.provide_message_feedback(
            message_id=message_id,
            is_helpful=validated_data['is_helpful'],
            feedback_notes=validated_data.get('feedback_notes', '')
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'Feedback recorded successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Message not found or feedback could not be recorded'
            }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error in message_feedback: {str(e)}")
        return Response({
            'error': 'An error occurred while recording feedback.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatPreferencesView(generics.RetrieveUpdateAPIView):
    """Get or update user's chat preferences."""
    serializer_class = ChatPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        service = ChatAssistantService()
        return service.get_or_create_preferences(self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_suggestions(request, session_id=None):
    """Get contextual chat suggestions."""
    try:
        if session_id:
            session = get_object_or_404(
                ChatSession, 
                id=session_id, 
                user=request.user
            )
        else:
            # Create a temporary session for suggestions
            service = ChatAssistantService()
            session = ChatSession(
                user=request.user,
                context_type=request.GET.get('context_type', 'blog_writing')
            )
        
        service = ChatAssistantService()
        suggestions = service.get_chat_suggestions(session)
        
        return Response({
            'suggestions': suggestions
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return Response({
            'suggestions': []
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_status(request):
    """Get chat assistant system status."""
    try:
        service = ChatAssistantService()
        
        # Get RAG system status if available
        if service.rag_system:
            rag_status = service.rag_system.get_system_status()
        else:
            rag_status = {
                'is_ready': False,
                'using_mock_generator': True,
                'error': 'RAG system not available'
            }
        
        return Response({
            'chat_service_initialized': service.is_initialized,
            'rag_system_status': rag_status,
            'version': '1.0.0'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return Response({
            'error': 'Could not retrieve system status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
