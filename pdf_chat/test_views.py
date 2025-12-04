from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def test_upload(request):
    """Simple test endpoint for file uploads"""
    try:
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request FILES: {request.FILES}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"User: {request.user}")
        
        files = request.FILES.getlist('files')
        logger.info(f"Files received: {len(files)}")
        
        if not files:
            return Response({
                'error': 'No files uploaded',
                'debug': {
                    'request_files': dict(request.FILES),
                    'request_data': dict(request.data),
                    'content_type': request.content_type,
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file_info = []
        for file in files:
            file_info.append({
                'name': file.name,
                'size': file.size,
                'content_type': file.content_type,
            })
        
        return Response({
            'success': True,
            'message': f'Received {len(files)} files',
            'files': file_info,
            'user': request.user.username
        })
        
    except Exception as e:
        logger.error(f"Upload test error: {e}")
        return Response({
            'error': str(e),
            'debug': {
                'request_method': request.method,
                'content_type': getattr(request, 'content_type', 'unknown'),
                'user': str(request.user),
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def test_endpoint(request):
    """Simple test endpoint"""
    return Response({
        'message': 'PDF Chat API is working',
        'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
        'timestamp': '2025-09-20 03:12:00'
    })