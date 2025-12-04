#!/usr/bin/env python
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_backend.settings')
django.setup()

from django.contrib.auth.models import User
from blogs.models import Blog
from comments.models import Comment
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import requests

def debug_comments():
    print("=== Comment System Debug ===\n")
    
    # Find active users and blogs
    active_users = User.objects.filter(is_active=True)
    blogs = Blog.objects.filter(is_published=True)
    
    print(f"Active users: {active_users.count()}")
    print(f"Published blogs: {blogs.count()}")
    
    if not active_users.exists():
        print("❌ No active users found")
        return
        
    if not blogs.exists():
        print("❌ No published blogs found")
        return
    
    # Get first active user and blog
    test_user = active_users.first()
    test_blog = blogs.first()
    
    print(f"Test user: {test_user.username}")
    print(f"Test blog: {test_blog.title} (ID: {test_blog.id})")
    
    # Test 1: Direct Django model creation
    print("\n--- Test 1: Direct Django Model ---")
    try:
        comment = Comment.objects.create(
            blog=test_blog,
            author=test_user,
            content="This is a test comment created directly via Django model"
        )
        print(f"✅ Direct model creation successful: Comment ID {comment.id}")
    except Exception as e:
        print(f"❌ Direct model creation failed: {str(e)}")
    
    # Test 2: API Test with DRF test client
    print("\n--- Test 2: DRF Test Client ---")
    try:
        client = APIClient()
        
        # Get JWT token for user
        refresh = RefreshToken.for_user(test_user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Test comment creation
        url = f'/api/comments/blog/{test_blog.id}/'
        data = {'content': 'This is a test comment via API'}
        
        response = client.post(url, data, format='json')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.data}")
        
        if response.status_code == 201:
            print("✅ API comment creation successful")
        else:
            print(f"❌ API comment creation failed: {response.data}")
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
    
    # Test 3: Check comment serializer validation
    print("\n--- Test 3: Serializer Validation ---")
    try:
        from comments.serializers import CommentCreateSerializer
        
        # Test valid data
        valid_data = {
            'content': 'Valid comment content',
            'blog': test_blog.id
        }
        
        serializer = CommentCreateSerializer(data=valid_data)
        if serializer.is_valid():
            print("✅ Serializer validation passed")
        else:
            print(f"❌ Serializer validation failed: {serializer.errors}")
        
        # Test invalid data (empty content)
        invalid_data = {
            'content': '',
            'blog': test_blog.id
        }
        
        serializer = CommentCreateSerializer(data=invalid_data)
        if not serializer.is_valid():
            print("✅ Serializer correctly rejects empty content")
        else:
            print("❌ Serializer incorrectly accepts empty content")
            
    except Exception as e:
        print(f"❌ Serializer test failed: {str(e)}")
    
    # Test 4: Check URL routing
    print("\n--- Test 4: URL Resolution ---")
    try:
        from django.urls import reverse
        
        # Test comment list URL
        url = reverse('comment_list_create', kwargs={'blog_id': test_blog.id})
        print(f"✅ Comment list URL resolves to: {url}")
        
    except Exception as e:
        print(f"❌ URL resolution failed: {str(e)}")
    
    # Show existing comments
    print(f"\n--- Existing Comments ---")
    comments = Comment.objects.filter(blog=test_blog, is_active=True)
    print(f"Total comments for blog '{test_blog.title}': {comments.count()}")
    for comment in comments[:5]:  # Show first 5
        print(f"- {comment.author.username}: {comment.content[:50]}...")

if __name__ == "__main__":
    debug_comments()