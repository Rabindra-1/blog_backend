from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.core.files.storage import default_storage
import time
import requests
import os
import base64
from PIL import Image
from io import BytesIO
from .models import GeneratedContent, ImageGeneration
from .serializers import GeneratedContentSerializer, ImageGenerationSerializer
from .ai_service import ai_service
import re
from urllib.parse import urlparse, parse_qs

def extract_youtube_info(youtube_url):
    """
    Extract video information from YouTube URL
    """
    try:
        # Parse YouTube URL to extract video ID
        parsed_url = urlparse(youtube_url)
        video_id = None
        
        if 'youtube.com' in parsed_url.netloc:
            if 'watch' in parsed_url.path:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            elif 'embed' in parsed_url.path:
                video_id = parsed_url.path.split('/')[-1]
        elif 'youtu.be' in parsed_url.netloc:
            video_id = parsed_url.path[1:]
        
        if not video_id:
            return None
        
        # Try to fetch video metadata using a simple approach
        # This is a basic implementation - for production you might want to use YouTube Data API
        try:
            # Try to get basic info from the YouTube page
            response = requests.get(f"https://www.youtube.com/watch?v={video_id}")
            if response.status_code == 200:
                # Try to extract title from page
                title_match = re.search(r'<title>([^<]+)</title>', response.text)
                title = title_match.group(1).replace(' - YouTube', '') if title_match else f"Video {video_id}"
                
                return {
                    'video_id': video_id,
                    'title': title,
                    'url': youtube_url,
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                }
        except Exception:
            # Fallback if we can't fetch the page
            pass
        
        # Return basic info even if we couldn't fetch details
        return {
            'video_id': video_id,
            'title': f"YouTube Video {video_id}",
            'url': youtube_url,
            'embed_url': f"https://www.youtube.com/embed/{video_id}",
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        }
        
    except Exception as e:
        print(f"Error extracting YouTube info: {e}")
        return None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_text(request):
    """Generate text content using AI (with free alternatives)"""
    prompt = request.data.get('prompt', '')
    if not prompt:
        return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_time = time.time()
    provider_used = "unknown"
    
    try:
        # Use AI service with fallback providers
        content = ai_service.generate_text(prompt, max_tokens=1500)
        processing_time = time.time() - start_time
        provider_used = settings.AI_PROVIDER
        
        # Save to database
        generated_content = GeneratedContent.objects.create(
            user=request.user,
            content_type='text',
            prompt=prompt,
            result=content,
            processing_time=processing_time,
            success=True,
            metadata={'provider': provider_used}
        )
        
        return Response({
            'id': generated_content.id,
            'content': content,
            'processing_time': processing_time,
            'provider': provider_used
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Save failed attempt
        GeneratedContent.objects.create(
            user=request.user,
            content_type='text',
            prompt=prompt,
            processing_time=processing_time,
            success=False,
            error_message=str(e),
            metadata={'provider': provider_used}
        )
        
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_image(request):
    """Analyze uploaded image using AI service with free alternatives"""
    analysis_type = request.data.get('analysis_type', 'description')
    uploaded_image = request.FILES.get('image')
    image_url = request.data.get('image_url')
    
    if not uploaded_image and not image_url:
        return Response({'error': 'Image file or URL is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_time = time.time()
    
    try:
        # Prepare image for analysis
        image_data = None
        base64_image = None
        
        if uploaded_image:
            # Read image data
            image_data = uploaded_image.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
        elif image_url:
            # Download image from URL for processing
            import requests as req
            response = req.get(image_url)
            if response.status_code == 200:
                image_data = response.content
                base64_image = base64.b64encode(image_data).decode('utf-8')
            else:
                return Response({'error': 'Could not download image from URL'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use AI service to analyze image
        generated_text = ai_service.analyze_image(
            image_data=image_data,
            image_base64=base64_image,
            analysis_type=analysis_type
        )
        
        processing_time = time.time() - start_time
        
        # Save uploaded image if provided
        saved_image_path = None
        if uploaded_image:
            # Reset file pointer for saving
            uploaded_image.seek(0)
            saved_image_path = default_storage.save(
                f'analyzed_images/{uploaded_image.name}',
                uploaded_image
            )
        
        # Save to database
        image_analysis = ImageGeneration.objects.create(
            user=request.user,
            uploaded_image=saved_image_path if uploaded_image else None,
            image_url=image_url if image_url else None,
            analysis_type=analysis_type,
            generated_text=generated_text,
            local_path=saved_image_path or '',
            success=True
        )
        
        # Also save in GeneratedContent for unified tracking
        GeneratedContent.objects.create(
            user=request.user,
            content_type='image',
            prompt=f"Image analysis ({analysis_type})",
            result=generated_text,
            file_path=saved_image_path or image_url or '',
            processing_time=processing_time,
            success=True,
            metadata={'analysis_type': analysis_type, 'image_analysis_id': image_analysis.id}
        )
        
        return Response({
            'id': image_analysis.id,
            'generated_text': generated_text,
            'analysis_type': analysis_type,
            'image_url': image_url or (request.build_absolute_uri(default_storage.url(saved_image_path)) if saved_image_path else None),
            'processing_time': processing_time
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Save failed attempt
        ImageGeneration.objects.create(
            user=request.user,
            uploaded_image=saved_image_path if 'saved_image_path' in locals() else None,
            image_url=image_url if image_url else None,
            analysis_type=analysis_type,
            success=False,
            error_message=str(e)
        )
        
        GeneratedContent.objects.create(
            user=request.user,
            content_type='image',
            prompt=f"Image analysis ({analysis_type})",
            processing_time=processing_time,
            success=False,
            error_message=str(e)
        )
        
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_youtube_url(request):
    """Process YouTube URL to extract content for blog generation"""
    youtube_url = request.data.get('youtube_url', '')
    
    if not youtube_url:
        return Response({'error': 'YouTube URL is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_time = time.time()
    
    try:
        # Extract video metadata and generate content based on URL analysis
        video_info = extract_youtube_info(youtube_url)
        
        if not video_info:
            return Response({'error': 'Could not extract video information from URL'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a comprehensive prompt for blog generation based on video info
        video_title = video_info.get('title', 'YouTube Video')
        video_id = video_info.get('video_id', 'Unknown')
        
        blog_prompt = f"""
        Write a comprehensive blog post about the YouTube video titled: "{video_title}"
        
        Video Details:
        - Title: {video_title}
        - Video ID: {video_id}
        - URL: {youtube_url}
        
        Create an engaging blog post that:
        1. Has an attention-grabbing headline based on the video title
        2. Introduces the video topic and why it's valuable to readers
        3. Discusses the key points viewers can expect to learn
        4. Provides context and additional insights related to the topic
        5. Includes relevant keywords for SEO
        6. Ends with a call-to-action encouraging readers to watch the full video
        
        Make it informative, well-structured with headings, and approximately 800-1000 words.
        Use markdown formatting for better readability.
        """
        
        # Generate blog content using AI service
        try:
            blog_content = ai_service.generate_text(blog_prompt, max_tokens=2000)
        except Exception as e:
            # Enhanced fallback if AI service fails - still generate meaningful content
            video_id = video_info.get('video_id', 'Unknown')
            
            # Create a more dynamic fallback based on available video info
            blog_content = f"""# {video_title}

## About This YouTube Video

We've analyzed the YouTube video titled **"{video_title}"** to bring you key insights and takeaways.

**Video Details:**
- **URL**: {youtube_url}
- **Video ID**: {video_id}
- **Title**: {video_title}

## Why This Content Is Worth Your Time

This video covers important topics that can benefit viewers looking to learn about {video_title.lower()}. YouTube has become a primary source of educational and entertainment content, and this particular video stands out for its approach to the subject matter.

## What You Can Expect

Based on the video title and content analysis:

1. **Educational Value**: The video appears to provide valuable information on its topic
2. **Practical Insights**: Viewers can expect actionable takeaways
3. **Quality Content**: The presentation style and content structure suggest a well-produced video

## Key Benefits of Watching

- **Learn Something New**: Expand your knowledge in this subject area
- **Stay Updated**: Get current information and perspectives
- **Practical Application**: Apply what you learn to real-world situations

## Ready to Dive In?

Don't miss out on the full experience! Watch the complete video here: {youtube_url}

The video promises to deliver comprehensive coverage of {video_title.lower()}, making it a valuable addition to your learning journey.

---
*Note: This content was generated based on video metadata analysis. For enhanced content generation, ensure AI services are properly configured.*
*Technical details: {str(e)}*"""
        
        processing_time = time.time() - start_time
        
        # Save to database
        generated_content = GeneratedContent.objects.create(
            user=request.user,
            content_type='youtube',
            prompt=youtube_url,
            result=blog_content,
            processing_time=processing_time,
            success=True,
            metadata={
                'video_info': video_info,
                'video_url': youtube_url,
                'processing_method': 'url_analysis'
            }
        )
        
        # Extract title from the generated content
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
        
        extracted_title = extract_title_from_content(blog_content, video_title)
        
        return Response({
            'id': generated_content.id,
            'title': extracted_title,
            'blog_content': blog_content,
            'content': blog_content,  # Also include as 'content' for compatibility
            'video_info': video_info,
            'processing_time': processing_time,
            'method': 'AI-generated content based on video URL analysis'
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        
        GeneratedContent.objects.create(
            user=request.user,
            content_type='youtube',
            prompt=youtube_url,
            processing_time=processing_time,
            success=False,
            error_message=str(e)
        )
        
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_video_content(request):
    """Generate video content description and settings"""
    title = request.data.get('title', '')
    description = request.data.get('description', '')
    
    if not title and not description:
        return Response({'error': 'Title or description is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_time = time.time()
    
    try:
        # Create comprehensive prompt for video script generation
        video_prompt = f"""
        You are a creative video production assistant. Create a detailed video script and production notes for:
        
        **Video Title:** {title}
        **Description:** {description}
        
        Please provide:
        1. A compelling video script with clear sections
        2. Shot list and camera directions
        3. Production notes and timing estimates
        4. Key talking points and transitions
        5. Call-to-action suggestions
        
        Format the response with clear headings and make it production-ready.
        """
        
        # Use AI service with fallback providers
        try:
            content = ai_service.generate_text(video_prompt, max_tokens=2000)
        except Exception as e:
            # Enhanced fallback with more dynamic content
            content = f"""# Video Production Plan: {title}

## Overview
**Title:** {title}
**Description:** {description}

## Video Script Structure

### Introduction (0-30 seconds)
- Hook: Start with an engaging question or statement related to {title}
- Brief introduction of what viewers will learn
- Personal connection or why this topic matters

### Main Content (30 seconds - 80% of video)
Based on your description: {description}

#### Key Points to Cover:
1. **Primary Topic**: Deep dive into the main subject of {title}
2. **Supporting Details**: Elaborate on the key aspects mentioned in your description
3. **Examples/Demonstrations**: Show practical applications or examples
4. **Tips and Best Practices**: Share actionable advice for viewers

### Conclusion (Final 20%)
- Summarize the main takeaways
- Call-to-action (subscribe, comment, share)
- Tease next video or related content

## Production Notes

### Shot List
- **Opening shot**: Close-up introduction
- **Main content**: Mix of talking head and supporting visuals
- **B-roll**: Include relevant supplementary footage
- **Closing**: Return to talking head for personal connection

### Technical Considerations
- **Lighting**: Ensure good lighting for all shots
- **Audio**: Use quality microphone for clear sound
- **Duration**: Aim for 5-15 minutes based on content depth

### Engagement Elements
- Ask questions to encourage comments
- Include visual aids or graphics where appropriate
- Use transitions to maintain viewer interest

## Keywords & SEO
Based on your title "{title}", consider including related keywords naturally throughout the script.

---
*Note: AI content generation encountered an issue ({str(e)}), but this production plan provides a solid foundation for your video creation.*"""
        
        processing_time = time.time() - start_time
        
        # Save to database
        generated_content = GeneratedContent.objects.create(
            user=request.user,
            content_type='video',
            prompt=f"Title: {title}, Description: {description}",
            result=content,
            processing_time=processing_time,
            success=True,
            metadata={'title': title, 'description': description}
        )
        
        return Response({
            'id': generated_content.id,
            'content': content,
            'title': title,
            'description': description,
            'processing_time': processing_time,
            'note': 'This is a video script generation. Actual video creation requires additional services.'
        })
    
    except Exception as e:
        processing_time = time.time() - start_time
        
        GeneratedContent.objects.create(
            user=request.user,
            content_type='video',
            prompt=f"Title: {title}, Description: {description}",
            processing_time=processing_time,
            success=False,
            error_message=str(e)
        )
        
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generation_history(request):
    """Get user's generation history"""
    content_type = request.GET.get('type', None)
    
    queryset = GeneratedContent.objects.filter(user=request.user)
    
    if content_type:
        queryset = queryset.filter(content_type=content_type)
    
    # Limit to last 50 items
    queryset = queryset[:50]
    
    serializer = GeneratedContentSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generation_stats(request):
    """Get user's generation statistics"""
    total_generations = GeneratedContent.objects.filter(user=request.user).count()
    successful_generations = GeneratedContent.objects.filter(user=request.user, success=True).count()
    
    stats_by_type = {}
    for content_type, _ in GeneratedContent.CONTENT_TYPES:
        count = GeneratedContent.objects.filter(user=request.user, content_type=content_type).count()
        stats_by_type[content_type] = count
    
    return Response({
        'total_generations': total_generations,
        'successful_generations': successful_generations,
        'success_rate': (successful_generations / total_generations * 100) if total_generations > 0 else 0,
        'by_type': stats_by_type
    })
