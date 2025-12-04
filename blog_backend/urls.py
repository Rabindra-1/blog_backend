"""
URL configuration for blog_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from debug_urls import debug_endpoint, debug_upload

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/blogs/', include('blogs.urls')),
    path('api/comments/', include('comments.urls')),
    path('api/ai/', include('ai_generation.urls')),
    path('api/chat/', include('chat_assistant.urls')),
    path('api/pdf-chat/', include('pdf_chat.urls')),
    # Debug endpoints
    path('debug/', debug_endpoint, name='debug'),
    path('debug-upload/', debug_upload, name='debug_upload'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
