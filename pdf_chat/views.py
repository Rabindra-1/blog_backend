from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os
import time
from .models import PDFDocument, ChatSession, ChatMessage
from .simple_processor import SimplePDFProcessor
import logging

logger = logging.getLogger(__name__)

# Global processor instance (in production, use Redis or database)
processors = {}

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_pdfs(request):
    """Upload and process PDF files"""
    try:
        files = request.FILES.getlist('files')
        
        if not files:
            return Response({
                'error': 'No files uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a new session
        session = ChatSession.objects.create(
            user=request.user,
            title=f"PDF Chat - {time.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Initialize processor for this session
        processor = SimplePDFProcessor()
        logger.info(f"Processing {len(files)} files for user {request.user.username}")
        
        # Process the uploaded files
        pdf_files = []
        saved_documents = []
        
        for file in files:
            if not file.name.lower().endswith('.pdf'):
                continue
                
            # Save file to storage
            file_path = default_storage.save(
                f'pdf_chat/{request.user.id}/{file.name}',
                ContentFile(file.read())
            )
            
            # Create database record
            pdf_doc = PDFDocument.objects.create(
                user=request.user,
                filename=file.name,
                file_path=file_path,
                file_size=file.size
            )
            
            session.documents.add(pdf_doc)
            saved_documents.append(pdf_doc)
            
            # Reset file pointer for processing
            file.seek(0)
            pdf_files.append(file)
        
        if not pdf_files:
            return Response({
                'error': 'No valid PDF files found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process PDFs
        result = processor.process_pdfs(pdf_files)
        
        if result['success']:
            # Store processor in memory (use Redis in production)
            processors[str(session.id)] = processor
            
            # Update document status
            for doc in saved_documents:
                doc.processed = True
                doc.save()
            
            # Store processor in memory for this session
            # In production, you'd want to use Redis or database storage
            
            return Response({
                'session_id': str(session.id),
                'message': result['message'],
                'processed_files': result['processed_files'],
                'total_text_length': result.get('total_text_length', 0)
            })
        else:
            # Mark documents as failed
            for doc in saved_documents:
                doc.processing_error = result['error']
                doc.save()
            
            return Response({
                'error': result['error'],
                'message': result['message']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_question(request):
    """Ask a question about uploaded PDFs"""
    try:
        session_id = request.data.get('session_id')
        question = request.data.get('question', '').strip()
        
        if not session_id:
            return Response({
                'error': 'Session ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not question:
            return Response({
                'error': 'Question is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get session
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get processor from memory
        processor = processors.get(session_id)
        if not processor:
            return Response({
                'error': 'Session data not found. Please upload PDFs again.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=question
        )
        
        # Get answer from processor
        start_time = time.time()
        result = processor.ask_question(question)
        processing_time = time.time() - start_time
        
        if result['success']:
            # Save assistant message
            assistant_message = ChatMessage.objects.create(
                session=session,
                sender='assistant',
                content=result['answer']
            )
            
            return Response({
                'answer': result['answer'],
                'question': question,
                'processing_time': processing_time,
                'message_id': str(assistant_message.id)
            })
        else:
            return Response({
                'error': result['error'],
                'answer': result['answer']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sessions(request):
    """Get user's chat sessions"""
    try:
        sessions = ChatSession.objects.filter(user=request.user)
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': str(session.id),
                'title': session.title,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'document_count': session.documents.count(),
                'message_count': session.messages.count()
            })
        
        return Response({
            'sessions': sessions_data
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_messages(request, session_id):
    """Get messages for a specific session"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = session.messages.all()
        
        messages_data = []
        for message in messages:
            messages_data.append({
                'id': str(message.id),
                'sender': message.sender,
                'content': message.content,
                'timestamp': message.timestamp,
                'is_helpful': message.is_helpful
            })
        
        return Response({
            'messages': messages_data,
            'session': {
                'id': str(session.id),
                'title': session.title,
                'created_at': session.created_at
            }
        })
        
    except ChatSession.DoesNotExist:
        return Response({
            'error': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def provide_feedback(request):
    """Provide feedback on assistant messages"""
    try:
        message_id = request.data.get('message_id')
        is_helpful = request.data.get('is_helpful')
        
        if not message_id:
            return Response({
                'error': 'Message ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            message = ChatMessage.objects.get(
                id=message_id,
                session__user=request.user,
                sender='assistant'
            )
            message.is_helpful = is_helpful
            message.save()
            
            return Response({
                'message': 'Feedback saved successfully'
            })
            
        except ChatMessage.DoesNotExist:
            return Response({
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    """Delete a chat session"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        
        # Clean up processor from memory
        if session_id in processors:
            del processors[session_id]
        
        # Clean up session file
        session_file = f'pdf_chat_sessions/{session_id}.pkl'
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # Delete session and related data
        session.delete()
        
        return Response({
            'message': 'Session deleted successfully'
        })
        
    except ChatSession.DoesNotExist:
        return Response({
            'error': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)