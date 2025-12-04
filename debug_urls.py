from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["GET", "POST"])
def debug_endpoint(request):
    """Simple debug endpoint without authentication"""
    return JsonResponse({
        'message': 'Debug endpoint working',
        'method': request.method,
        'path': request.path,
        'user': str(request.user) if hasattr(request, 'user') else 'No user',
        'authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
    })

@csrf_exempt
@require_http_methods(["POST"])
def debug_upload(request):
    """Debug file upload endpoint"""
    try:
        files = request.FILES.getlist('files')
        return JsonResponse({
            'message': 'Debug upload working',
            'files_received': len(files),
            'file_names': [f.name for f in files],
            'user': str(request.user) if hasattr(request, 'user') else 'No user',
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Debug upload failed'
        }, status=500)