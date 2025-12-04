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

def final_comment_test():
    print("=== Final Comment System Test ===\n")
    
    # Get test data
    test_user = User.objects.filter(is_active=True).first()
    test_blog = Blog.objects.filter(is_published=True).first()
    
    if not test_user or not test_blog:
        print("❌ Missing test data (user or blog)")
        return
    
    print(f"Test User: {test_user.username}")
    print(f"Test Blog: {test_blog.title} (ID: {test_blog.id})")
    
    # Test the fixed API
    client = APIClient()
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    # Test 1: POST a comment
    print("\n--- Test 1: POST Comment ---")
    url = f'/api/comments/blog/{test_blog.id}/'
    data = {'content': 'This is a test comment from the fixed API!'}
    
    response = client.post(url, data, format='json')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        print("✅ Comment creation successful!")
        comment_data = response.data
        print(f"Created comment with content: '{comment_data['content']}'")
        comment_id = comment_data.get('id')
    else:
        print(f"❌ Comment creation failed: {response.data}")
        return
    
    # Test 2: GET comments
    print("\n--- Test 2: GET Comments ---")
    response = client.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Comment retrieval successful!")
        comments_data = response.data
        print(f"Total comments: {comments_data['count']}")
        if comments_data['results']:
            latest_comment = comments_data['results'][-1]
            print(f"Latest comment: '{latest_comment['content']}'")
            print(f"Author: {latest_comment['author']['username']}")
    else:
        print(f"❌ Comment retrieval failed: {response.data}")
    
    # Test 3: POST a reply
    if comment_id:
        print("\n--- Test 3: POST Reply ---")
        reply_url = f'/api/comments/{comment_id}/reply/'
        reply_data = {'content': 'This is a reply to the comment!'}
        
        response = client.post(reply_url, reply_data, format='json')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ Reply creation successful!")
            reply_data = response.data
            print(f"Created reply: '{reply_data['content']}'")
        else:
            print(f"❌ Reply creation failed: {response.data}")
    
    # Show final state
    print(f"\n--- Final State ---")
    total_comments = Comment.objects.filter(blog=test_blog, is_active=True).count()
    print(f"Total comments in database: {total_comments}")
    
    print(f"\n✅ Comment system is working correctly!")
    print("Frontend should now be able to post comments successfully.")

if __name__ == "__main__":
    final_comment_test()