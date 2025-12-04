from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, F
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
import requests
import tempfile
import os
import logging
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

from .models import Blog, BlogLike, BlogBookmark, Tag, Category, BlogImage, BlogVideo, BlogView
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    BlogCreateUpdateSerializer,
    BlogImageSerializer,
    BlogVideoSerializer,
    TagSerializer,
    CategorySerializer
)
from .pagination import CustomPageNumberPagination
from ai_generation.ai_service import ai_service

class BlogListCreateView(generics.ListCreateAPIView):
    queryset = Blog.objects.filter(is_published=True).select_related('author', 'category').prefetch_related('tags')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['layout_type', 'tags__name', 'author__username', 'category', 'category__slug', 'category__name']
    search_fields = ['title', 'content', 'tags__name', 'author__username', 'category__name']
    ordering_fields = ['created_at', 'likes_count', 'views_count', 'title']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BlogCreateUpdateSerializer
        return BlogListSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class BlogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.filter(is_published=True)
    lookup_field = 'slug'
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BlogCreateUpdateSerializer
        return BlogDetailSerializer
    
    def get_object(self):
        obj = super().get_object()
        # Track unique views
        self._track_view(obj)
        return obj
    
    def _track_view(self, blog):
        """Track unique views per user or IP address"""
        try:
            # Get client IP address
            x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = self.request.META.get('REMOTE_ADDR', '127.0.0.1')
            
            # Get user agent
            user_agent = self.request.META.get('HTTP_USER_AGENT', '')
            
            # Try to create a view record
            view_created = False
            
            if self.request.user.is_authenticated:
                # For authenticated users, track by user
                view, view_created = BlogView.objects.get_or_create(
                    blog=blog,
                    user=self.request.user,
                    defaults={
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                )
            else:
                # For anonymous users, track by IP
                view, view_created = BlogView.objects.get_or_create(
                    blog=blog,
                    ip_address=ip_address,
                    user=None,
                    defaults={
                        'user_agent': user_agent
                    }
                )
            
            # Only increment view count if this is a new view
            if view_created:
                Blog.objects.filter(pk=blog.pk).update(views_count=F('views_count') + 1)
        
        except IntegrityError as e:
            # Handle database constraint violations
            logger.warning(f"IntegrityError while tracking view for blog {blog.id}: {str(e)}")
        except Exception as e:
            # Log any other unexpected errors but don't crash the view
            logger.error(f"Unexpected error while tracking view for blog {blog.id}: {str(e)}")
    
    def perform_update(self, serializer):
        # Only allow author to update
        if serializer.instance.author != self.request.user:
            raise PermissionError("You can only edit your own blogs.")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only allow author to delete
        if instance.author != self.request.user:
            raise PermissionError("You can only delete your own blogs.")
        instance.delete()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id, is_published=True)
    like, created = BlogLike.objects.get_or_create(blog=blog, user=request.user)
    
    if not created:
        like.delete()
        blog.likes_count = max(0, blog.likes_count - 1)
        blog.save()
        return Response({'liked': False, 'likes_count': blog.likes_count})
    
    blog.likes_count += 1
    blog.save()
    return Response({'liked': True, 'likes_count': blog.likes_count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bookmark_blog(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id, is_published=True)
    bookmark, created = BlogBookmark.objects.get_or_create(blog=blog, user=request.user)
    
    if not created:
        bookmark.delete()
        return Response({'bookmarked': False})
    
    return Response({'bookmarked': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_blogs(request):
    blogs = Blog.objects.filter(author=request.user)
    serializer = BlogListSerializer(blogs, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bookmarked_blogs(request):
    bookmarked_blog_ids = BlogBookmark.objects.filter(user=request.user).values_list('blog_id', flat=True)
    blogs = Blog.objects.filter(id__in=bookmarked_blog_ids, is_published=True)
    serializer = BlogListSerializer(blogs, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blog_analytics(request):
    """Get blog view analytics"""
    from datetime import timedelta
    from django.utils import timezone
    
    # Only allow admins or superusers to view analytics
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Calculate recent views (last 7 days)
    recent_date = timezone.now() - timedelta(days=7)
    
    analytics_data = {
        'total_unique_views': BlogView.objects.count(),
        'authenticated_views': BlogView.objects.filter(user__isnull=False).count(),
        'anonymous_views': BlogView.objects.filter(user__isnull=True).count(),
        'recent_views_7_days': BlogView.objects.filter(created_at__gte=recent_date).count(),
        'top_blogs': []
    }
    
    # Get top 10 most viewed blogs
    top_blogs = Blog.objects.filter(is_published=True).order_by('-views_count')[:10]
    for blog in top_blogs:
        analytics_data['top_blogs'].append({
            'id': blog.id,
            'title': blog.title,
            'slug': blog.slug,
            'views_count': blog.views_count,
            'author': blog.author.username if blog.author else 'Unknown'
        })
    
    return Response(analytics_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_blog_content(request):
    prompt = request.data.get('prompt', '')
    if not prompt:
        return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Use AI service with fallback providers
        blog_prompt = f"Write a blog post about: {prompt}"
        content = ai_service.generate_text(blog_prompt, max_tokens=1500)
        
        # Generate a title from the first line or create one
        lines = content.split('\n')
        title = lines[0].strip().replace('#', '').strip() if lines else f"Blog about {prompt}"
        
        return Response({
            'title': title,
            'content': content,
            'provider': settings.AI_PROVIDER
        })
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def extract_youtube_audio_url(youtube_url):
    """Extract YouTube video ID and return download info"""
    try:
        # Parse YouTube URL
        parsed_url = urlparse(youtube_url)
        if 'youtube.com' in parsed_url.netloc:
            video_id = parse_qs(parsed_url.query)['v'][0]
        elif 'youtu.be' in parsed_url.netloc:
            video_id = parsed_url.path[1:]
        else:
            return None
        
        return f"https://www.youtube.com/watch?v={video_id}"
    except:
        return None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def generate_blog_from_video(request):
    youtube_url = request.data.get('youtube_url', '')
    video_file = request.FILES.get('video_file')
    
    if not youtube_url and not video_file:
        return Response({'error': 'Either YouTube URL or video file is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        transcript = ""
        # Note: Whisper processing for uploaded files would require additional setup
        
        if video_file:
            # Video file processing would require Whisper setup
            return Response({
                'error': 'Video file processing requires additional setup. Please use YouTube URLs instead.',
                'suggestion': 'Try using a YouTube URL for AI-powered blog generation'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
        
        elif youtube_url:
            # Process YouTube URL using our AI service
            from ai_generation.views import extract_youtube_info
            
            video_info = extract_youtube_info(youtube_url)
            if not video_info:
                return Response({'error': 'Could not extract video information from URL'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create targeted blog content based on video info
            video_title = video_info.get('title', 'YouTube Video')
            blog_prompt = f'Write a comprehensive blog post about the YouTube video titled: "{video_title}". Make it engaging with proper formatting, headings, and around 800-1000 words. Include an introduction, key points about the video content, and a conclusion encouraging readers to watch the video.'
            
            try:
                content = ai_service.generate_text(blog_prompt, max_tokens=2000)
                
                # Extract title from the generated content with better formatting handling
                def extract_title_from_content(content, fallback_title):
                    lines = content.split('\n')
                    if lines and lines[0].strip():
                        # Clean up the title - remove markdown formatting, asterisks, quotes
                        raw_title = lines[0].strip()
                        title = raw_title.replace('#', '').replace('**', '').replace('*', '').strip()
                        # Remove surrounding quotes if present
                        if title.startswith('"') and title.endswith('"'):
                            title = title[1:-1].strip()
                        # If title is empty after cleaning, use fallback
                        return title if title else fallback_title
                    return fallback_title
                
                title = extract_title_from_content(content, video_title)
                
                return Response({
                    'title': title,
                    'content': content,
                    'video_info': video_info,
                    'method': 'AI-generated from YouTube URL'
                })
            except Exception as e:
                # Enhanced fallback content if AI generation fails
                title = video_title if not video_title.startswith('Video ') else f"Exploring {video_title}"
                content = f"""# {title}

## Introduction

Today we're diving into an insightful YouTube video titled **"{video_title}"** that offers valuable perspectives worth exploring in depth.

**Video Information:**
- **Title**: {video_title}
- **URL**: {youtube_url}
- **Video ID**: {video_info.get('video_id', 'Unknown')}

## What Makes This Video Special

The video "{video_title}" stands out for several reasons. Based on the title and available information, this content appears to address important topics that resonate with today's audience.

### Key Aspects

**Educational Value**: Videos like this contribute to our understanding of complex topics by breaking them down into accessible content.

**Practical Application**: The insights shared in this video can likely be applied to real-world situations, making it more than just theoretical knowledge.

**Community Impact**: Quality content creators help build informed communities by sharing knowledge and facilitating discussions.

## Why You Should Watch

Here are compelling reasons to check out the full video:

- **Comprehensive Coverage**: The full video provides context that can't be captured in a summary
- **Visual Learning**: Video content often includes demonstrations, examples, and visual aids
- **Creator's Perspective**: Get the content directly from the source with the creator's unique insights
- **Community Discussion**: Join the conversation in the comments section

## Your Next Step

Ready to explore this content? Watch the full video here: {youtube_url}

The video promises to deliver valuable insights about {video_title.lower()}, making it a worthwhile addition to your learning journey.

---
*Note: This content was generated based on video metadata analysis. The full video contains additional details and context.*
*AI Service Status: {str(e)}*"""
                
                return Response({
                    'title': title,
                    'content': content,
                    'video_info': video_info,
                    'method': 'Fallback content due to AI error',
                    'error': str(e)
                })
    
    except Exception as e:
        return Response({'error': f'Error processing video: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([])
def tags(request):
    tags = Tag.objects.all().order_by('name')
    serializer = TagSerializer(tags, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([])
def categories(request):
    categories = Category.objects.all().order_by('name')
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def add_blog_image(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id, author=request.user)
    
    image = request.FILES.get('image')
    caption = request.data.get('caption', '')
    order = request.data.get('order', 0)
    
    if not image:
        return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    blog_image = BlogImage.objects.create(
        blog=blog,
        image=image,
        caption=caption,
        order=order
    )
    
    serializer = BlogImageSerializer(blog_image)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def add_blog_video(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id, author=request.user)
    
    video = request.FILES.get('video')
    thumbnail = request.FILES.get('thumbnail')
    caption = request.data.get('caption', '')
    order = request.data.get('order', 0)
    
    if not video:
        return Response({'error': 'Video file is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    blog_video = BlogVideo.objects.create(
        blog=blog,
        video=video,
        thumbnail=thumbnail,
        caption=caption,
        order=order
    )
    
    serializer = BlogVideoSerializer(blog_video)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_blog_image(request, image_id):
    image = get_object_or_404(BlogImage, id=image_id, blog__author=request.user)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_blog_video(request, video_id):
    video = get_object_or_404(BlogVideo, id=video_id, blog__author=request.user)
    video.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
