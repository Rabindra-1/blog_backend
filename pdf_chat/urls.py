from django.urls import path
from . import views, test_views, enhanced_views

urlpatterns = [
    # Test endpoints
    path('test/', test_views.test_endpoint, name='test_endpoint'),
    path('test-upload/', test_views.test_upload, name='test_upload'),
    
    # Enhanced endpoints (new)
    path('preloaded/', enhanced_views.get_preloaded_documents, name='get_preloaded_documents'),
    path('create-session/', enhanced_views.create_session_with_preloaded, name='create_session_with_preloaded'),
    path('upload-user/', enhanced_views.upload_user_pdfs, name='upload_user_pdfs'),
    path('ask-enhanced/', enhanced_views.ask_enhanced_question, name='ask_enhanced_question'),
    path('sessions-enhanced/', enhanced_views.get_enhanced_sessions, name='get_enhanced_sessions'),
    path('setup-folder/', enhanced_views.setup_preloaded_folder, name='setup_preloaded_folder'),
    
    # Original endpoints (kept for compatibility)
    path('upload/', views.upload_pdfs, name='upload_pdfs'),
    path('ask/', views.ask_question, name='ask_question'),
    path('sessions/', views.get_sessions, name='get_sessions'),
    path('sessions/<uuid:session_id>/', views.get_session_messages, name='get_session_messages'),
    path('feedback/', views.provide_feedback, name='provide_feedback'),
    path('sessions/<uuid:session_id>/delete/', views.delete_session, name='delete_session'),
]