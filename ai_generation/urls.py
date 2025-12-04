from django.urls import path
from . import views

urlpatterns = [
    path('text/', views.generate_text, name='generate_text'),
    path('image/', views.analyze_image, name='analyze_image'),
    path('youtube/', views.process_youtube_url, name='process_youtube'),
    path('video/', views.generate_video_content, name='generate_video'),
    path('history/', views.generation_history, name='generation_history'),
    path('stats/', views.generation_stats, name='generation_stats'),
]
