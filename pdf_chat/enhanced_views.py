from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import uuid
import os
import time
from .models import PDFDocument, ChatSession, ChatMessage
from .enhanced_processor import EnhancedPDFProcessor
import logging

logger = logging.getLogger(__name__)

# Global processor instances (in production, use Redis or database)
processors = {}

# Pre-loaded documents folder
PRELOADED_DOCS_FOLDER = os.path.join(settings.BASE_DIR, 'preloaded_pdfs')

@api_view(['GET'])
def get_preloaded_documents(request):
    """Get list of pre-loaded documents"""
    try:
        # Create processor to check pre-loaded documents
        processor = EnhancedPDFProcessor(preload_folder=PRELOADED_DOCS_FOLDER)
        doc_info = processor.get_available_documents()
        
        return Response({
            'preloaded_documents': doc_info['preloaded_documents'],
            'total_preloaded': len(doc_info['preloaded_documents']),
            'folder_path': PRELOADED_DOCS_FOLDER,
            'has_content': doc_info['has_content']
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'preloaded_documents': [],
            'total_preloaded': 0
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_session_with_preloaded(request):
    """Create a new session with pre-loaded documents"""
    try:
        # Create a new session
        session = ChatSession.objects.create(
            user=request.user,
            title=f"PDF Chat - {time.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Initialize processor with pre-loaded documents
        processor = EnhancedPDFProcessor(preload_folder=PRELOADED_DOCS_FOLDER)
        
        # Store processor in memory
        processors[str(session.id)] = processor
        
        doc_info = processor.get_available_documents()
        
        return Response({
            'session_id': str(session.id),
            'message': f"Session created with {len(doc_info['preloaded_documents'])} pre-loaded documents",
            'preloaded_documents': doc_info['preloaded_documents'],
            'ready_for_questions': doc_info['has_content']
        })
        
    except Exception as e:
        logger.error(f"Error creating session with pre-loaded docs: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_user_pdfs(request):
    """Upload user PDFs to existing session or create new session"""
    try:
        session_id = request.data.get('session_id')
        files = request.FILES.getlist('files')
        
        if not files:
            return Response({
                'error': 'No files uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
                processor = processors.get(session_id)
                if not processor:
                    # Recreate processor with pre-loaded documents
                    processor = EnhancedPDFProcessor(preload_folder=PRELOADED_DOCS_FOLDER)
                    processors[session_id] = processor
            except ChatSession.DoesNotExist:
                return Response({
                    'error': 'Session not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Create new session
            session = ChatSession.objects.create(
                user=request.user,
                title=f"PDF Chat - {time.strftime('%Y-%m-%d %H:%M')}"
            )
            processor = EnhancedPDFProcessor(preload_folder=PRELOADED_DOCS_FOLDER)
            processors[str(session.id)] = processor
            session_id = str(session.id)
        
        logger.info(f"Processing {len(files)} user files for session {session_id}")
        
        # Save uploaded files to storage
        pdf_files = []
        saved_documents = []
        
        for file in files:
            if not (file.name.lower().endswith('.pdf') or file.content_type == 'application/pdf'):
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
        
        # Process user PDFs
        result = processor.process_user_pdfs(pdf_files)
        
        if result['success']:
            # Update document status
            for doc in saved_documents:
                doc.processed = True
                doc.save()
            
            return Response({
                'session_id': session_id,
                'message': result['message'],
                'user_files': result['user_files'],
                'preloaded_files': result['preloaded_files'],
                'total_text_length': result['total_text_length']
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
        logger.error(f"Error in upload_user_pdfs: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_enhanced_question(request):
    """Ask a question with enhanced blog-style responses"""
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
            # Recreate processor with pre-loaded documents
            processor = EnhancedPDFProcessor(preload_folder=PRELOADED_DOCS_FOLDER)
            processors[session_id] = processor
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=question
        )
        
        # Get enhanced answer from processor
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
                'message_id': str(assistant_message.id),
                'sources': result.get('sources', {}),
                'documents_searched': result.get('documents_searched', 0)
            })
        else:
            return Response({
                'error': result['error'],
                'answer': result['answer']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error in ask_enhanced_question: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enhanced_sessions(request):
    """Get user's chat sessions with enhanced information"""
    try:
        sessions = ChatSession.objects.filter(user=request.user)
        
        sessions_data = []
        for session in sessions:
            # Get processor info if available
            processor = processors.get(str(session.id))
            doc_info = processor.get_available_documents() if processor else {
                'preloaded_documents': [],
                'user_documents': [],
                'total_documents': 0
            }
            
            sessions_data.append({
                'id': str(session.id),
                'title': session.title,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'document_count': session.documents.count(),
                'message_count': session.messages.count(),
                'preloaded_docs': len(doc_info['preloaded_documents']),
                'user_docs': len(doc_info['user_documents']),
                'total_docs': doc_info['total_documents']
            })
        
        return Response({
            'sessions': sessions_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_enhanced_sessions: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_preloaded_folder(request):
    """Setup the pre-loaded documents folder (admin function)"""
    try:
        # Create the folder if it doesn't exist
        os.makedirs(PRELOADED_DOCS_FOLDER, exist_ok=True)
        
        # Check if folder has PDFs
        pdf_files = []
        if os.path.exists(PRELOADED_DOCS_FOLDER):
            import glob
            pdf_files = glob.glob(os.path.join(PRELOADED_DOCS_FOLDER, "*.pdf"))
        
        return Response({
            'folder_path': PRELOADED_DOCS_FOLDER,
            'folder_exists': os.path.exists(PRELOADED_DOCS_FOLDER),
            'pdf_count': len(pdf_files),
            'pdf_files': [os.path.basename(f) for f in pdf_files],
            'message': f"Pre-loaded folder setup complete. Found {len(pdf_files)} PDF files."
        })
        
    except Exception as e:
        logger.error(f"Error setting up preloaded folder: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)