import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from .models import ChatSession, ChatMessage
# Always use SimpleChatService for now since the complex service has dependency issues
from .simple_service import SimpleChatService as ChatAssistantService
from .serializers import ChatMessageSerializer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat with AI assistant."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.user = None
        self.session_group_name = None
        self.chat_service = ChatAssistantService()
    
    async def connect(self):
        """Accept WebSocket connection and join chat session group."""
        # Get session ID from URL route
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user or self.user.is_anonymous:
            logger.warning("Unauthenticated user attempted WebSocket connection")
            await self.close()
            return
        
        # Verify session exists and belongs to user
        try:
            session = await self.get_chat_session(self.session_id, self.user)
            if not session:
                logger.warning(f"Session {self.session_id} not found or doesn't belong to user {self.user.id}")
                await self.close()
                return
        except Exception as e:
            logger.error(f"Error verifying session: {str(e)}")
            await self.close()
            return
        
        # Join session group
        self.session_group_name = f'chat_{self.session_id}'
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': str(self.session_id),
            'message': 'Connected to chat assistant'
        }))
        
        logger.info(f"User {self.user.id} connected to session {self.session_id}")
    
    async def disconnect(self, close_code):
        """Leave chat session group on disconnect."""
        if self.session_group_name:
            await self.channel_layer.group_discard(
                self.session_group_name,
                self.channel_name
            )
        
        logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from session {self.session_id}")
    
    async def receive(self, text_data):
        """Receive message from WebSocket and process it."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'message_feedback':
                await self.handle_message_feedback(data)
            else:
                await self.send_error('Unknown message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error('Error processing message')
    
    async def handle_chat_message(self, data):
        """Handle incoming chat message and generate AI response."""
        try:
            user_message = data.get('message', '').strip()
            if not user_message:
                await self.send_error('Empty message')
                return
            
            # Get context data
            context_data = {
                'blog_draft_content': data.get('blog_draft_content', ''),
                'target_section': data.get('target_section', ''),
                'include_blog_context': data.get('include_blog_context', True)
            }
            
            # Get the session
            session = await self.get_chat_session(self.session_id, self.user)
            if not session:
                await self.send_error('Session not found')
                return
            
            # Send typing indicator
            await self.send_to_group({
                'type': 'typing_indicator',
                'is_typing': True,
                'sender': 'assistant'
            })
            
            try:
                # Process message using the service (in sync context)
                ai_response = await database_sync_to_async(self.chat_service.process_message)(
                    session=session,
                    user_message=user_message,
                    context_data=context_data
                )
                
                # Serialize the response
                response_data = await database_sync_to_async(
                    lambda: ChatMessageSerializer(ai_response).data
                )()
                
                # Send AI response to the group
                await self.send_to_group({
                    'type': 'ai_response',
                    'message': response_data,
                    'session_updated': True
                })
                
            except Exception as e:
                logger.error(f"Error generating AI response: {str(e)}")
                await self.send_error('Failed to generate response')
            
            finally:
                # Stop typing indicator
                await self.send_to_group({
                    'type': 'typing_indicator',
                    'is_typing': False,
                    'sender': 'assistant'
                })
        
        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            await self.send_error('Error processing message')
    
    async def handle_typing_indicator(self, data):
        """Handle typing indicator from client."""
        await self.send_to_group({
            'type': 'typing_indicator',
            'is_typing': data.get('is_typing', False),
            'sender': 'user'
        })
    
    async def handle_message_feedback(self, data):
        """Handle feedback on AI messages."""
        try:
            message_id = data.get('message_id')
            is_helpful = data.get('is_helpful')
            feedback_notes = data.get('feedback_notes', '')
            
            if message_id is None or is_helpful is None:
                await self.send_error('Invalid feedback data')
                return
            
            # Record feedback using the service
            success = await database_sync_to_async(self.chat_service.provide_message_feedback)(
                message_id=message_id,
                is_helpful=is_helpful,
                feedback_notes=feedback_notes
            )
            
            if success:
                await self.send(text_data=json.dumps({
                    'type': 'feedback_recorded',
                    'message_id': message_id,
                    'success': True
                }))
            else:
                await self.send_error('Failed to record feedback')
                
        except Exception as e:
            logger.error(f"Error handling feedback: {str(e)}")
            await self.send_error('Error recording feedback')
    
    async def send_to_group(self, data):
        """Send message to all clients in the session group."""
        await self.channel_layer.group_send(
            self.session_group_name,
            {
                'type': 'chat_message',
                'data': data
            }
        )
    
    async def chat_message(self, event):
        """Receive message from group and send to WebSocket."""
        await self.send(text_data=json.dumps(event['data']))
    
    async def send_error(self, message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    @database_sync_to_async
    def get_chat_session(self, session_id, user):
        """Get chat session from database."""
        try:
            return ChatSession.objects.get(
                id=session_id,
                user=user,
                is_active=True
            )
        except ChatSession.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting chat session: {str(e)}")
            return None


class QuickChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for quick chat without persistent sessions."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.chat_service = ChatAssistantService()
    
    async def connect(self):
        """Accept WebSocket connection for quick chat."""
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user or self.user.is_anonymous:
            logger.warning("Unauthenticated user attempted quick chat WebSocket connection")
            await self.close()
            return
        
        # Accept connection
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to quick chat assistant'
        }))
        
        logger.info(f"User {self.user.id} connected to quick chat")
    
    async def disconnect(self, close_code):
        """Handle disconnect."""
        logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from quick chat")
    
    async def receive(self, text_data):
        """Receive message from WebSocket and process it."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'quick_chat_message':
                await self.handle_quick_chat_message(data)
            else:
                await self.send_error('Unknown message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error processing quick chat message: {str(e)}")
            await self.send_error('Error processing message')
    
    async def handle_quick_chat_message(self, data):
        """Handle quick chat message."""
        try:
            user_message = data.get('message', '').strip()
            if not user_message:
                await self.send_error('Empty message')
                return
            
            # Get context data
            context_data = {
                'blog_draft_content': data.get('blog_draft_content', ''),
                'target_section': data.get('target_section', ''),
                'include_blog_context': data.get('include_blog_context', True)
            }
            
            context_type = data.get('context_type', 'blog_writing')
            
            # Send typing indicator
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'is_typing': True,
                'sender': 'assistant'
            }))
            
            try:
                # Create temporary session
                temp_session = await database_sync_to_async(self.chat_service.create_chat_session)(
                    user=self.user,
                    context_type=context_type,
                    context_metadata={'temporary': True}
                )
                
                # Process message
                ai_response = await database_sync_to_async(self.chat_service.process_message)(
                    session=temp_session,
                    user_message=user_message,
                    context_data=context_data
                )
                
                # Serialize the response
                response_data = await database_sync_to_async(
                    lambda: ChatMessageSerializer(ai_response).data
                )()
                
                # Send response
                await self.send(text_data=json.dumps({
                    'type': 'quick_chat_response',
                    'message': response_data
                }))
                
                # Clean up temporary session
                await database_sync_to_async(temp_session.delete)()
                
            except Exception as e:
                logger.error(f"Error generating quick chat response: {str(e)}")
                await self.send_error('Failed to generate response')
            
            finally:
                # Stop typing indicator
                await self.send(text_data=json.dumps({
                    'type': 'typing_indicator',
                    'is_typing': False,
                    'sender': 'assistant'
                }))
        
        except Exception as e:
            logger.error(f"Error handling quick chat message: {str(e)}")
            await self.send_error('Error processing message')
    
    async def send_error(self, message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
