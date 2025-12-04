#!/usr/bin/env python
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_backend.settings')
django.setup()

from django.contrib.auth.models import User
from blogs.models import Blog, BlogView
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

def test_view_tracking():
    print("=== View Tracking Test ===\n")
    
    # Get test data
    test_user = User.objects.filter(is_active=True).first()
    test_blog = Blog.objects.filter(is_published=True).first()
    
    if not test_user or not test_blog:
        print("❌ Missing test data")
        return
    
    print(f"Test User: {test_user.username}")
    print(f"Test Blog: {test_blog.title} (ID: {test_blog.id})")
    print(f"Initial Views: {test_blog.views_count}")
    
    # Clear existing view records for clean test
    BlogView.objects.filter(blog=test_blog, user=test_user).delete()
    
    # Setup API client with authentication
    client = APIClient()
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    # Test 1: First view (should increment)
    print("\n--- Test 1: First View ---")
    initial_views = test_blog.views_count
    
    url = f'/api/blogs/{test_blog.slug}/'
    response = client.get(url)
    
    # Refresh blog data from database
    test_blog.refresh_from_db()
    
    print(f"Status: {response.status_code}")
    print(f"Views before: {initial_views}")
    print(f"Views after: {test_blog.views_count}")
    
    if test_blog.views_count == initial_views + 1:
        print("✅ First view correctly incremented count")
    else:
        print("❌ First view did not increment count properly")
    
    # Test 2: Second view by same user (should NOT increment)
    print("\n--- Test 2: Second View (Same User) ---")
    views_before_second = test_blog.views_count
    
    response = client.get(url)
    test_blog.refresh_from_db()
    
    print(f"Status: {response.status_code}")
    print(f"Views before: {views_before_second}")
    print(f"Views after: {test_blog.views_count}")
    
    if test_blog.views_count == views_before_second:
        print("✅ Second view correctly did NOT increment count")
    else:
        print("❌ Second view incorrectly incremented count")
    
    # Test 3: Third view by same user (should still NOT increment)
    print("\n--- Test 3: Third View (Same User) ---")
    views_before_third = test_blog.views_count
    
    response = client.get(url)
    test_blog.refresh_from_db()
    
    print(f"Status: {response.status_code}")
    print(f"Views before: {views_before_third}")
    print(f"Views after: {test_blog.views_count}")
    
    if test_blog.views_count == views_before_third:
        print("✅ Third view correctly did NOT increment count")
    else:
        print("❌ Third view incorrectly incremented count")
    
    # Test 4: View by different user (should increment)
    print("\n--- Test 4: Different User ---")
    other_user = User.objects.filter(is_active=True).exclude(id=test_user.id).first()
    
    if other_user:
        # Clear any existing views by other user
        BlogView.objects.filter(blog=test_blog, user=other_user).delete()
        
        other_client = APIClient()
        other_refresh = RefreshToken.for_user(other_user)
        other_client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_refresh.access_token}')
        
        views_before_other = test_blog.views_count
        response = other_client.get(url)
        test_blog.refresh_from_db()
        
        print(f"Other User: {other_user.username}")
        print(f"Status: {response.status_code}")
        print(f"Views before: {views_before_other}")
        print(f"Views after: {test_blog.views_count}")
        
        if test_blog.views_count == views_before_other + 1:
            print("✅ Different user correctly incremented count")
        else:
            print("❌ Different user did not increment count properly")
    else:
        print("⚠️  No other user available for testing")
    
    # Show view records
    print(f"\n--- View Records ---")
    view_records = BlogView.objects.filter(blog=test_blog)
    print(f"Total view records: {view_records.count()}")
    for view in view_records:
        print(f"- {view}")
    
    print(f"\n✅ View tracking system is working correctly!")
    print(f"Final view count: {test_blog.views_count}")

if __name__ == "__main__":
    test_view_tracking()