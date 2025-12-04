#!/usr/bin/env python
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import EmailVerification
from django.conf import settings
import requests

def test_email_verification():
    print("=== Email Verification Debug Test ===")
    
    # Test 1: Check Django settings
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Test 2: Test via Django directly (like console would do)
    print("--- Testing via Django directly ---")
    try:
        # Create test user
        username = "direct_test"
        email = "sahrabindra394@gmail.com"
        
        # Delete existing test user if exists
        User.objects.filter(username=username).delete()
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password="test123")
        user.is_active = False
        user.save()
        
        # Create verification
        verification = EmailVerification.objects.create(user=user)
        print(f"Created verification token: {verification.token}")
        
        # Send email
        verification.send_verification_email()
        print("✅ Direct Django email sending completed")
        
    except Exception as e:
        print(f"❌ Direct Django email failed: {str(e)}")
    
    print()
    
    # Test 3: Test via API call (like frontend would do)
    print("--- Testing via API call ---")
    try:
        api_url = "http://127.0.0.1:8000/api/auth/register/"
        data = {
            "username": "api_test",
            "email": "sahrabindra394@gmail.com",
            "password": "testpass123",
            "password_confirm": "testpass123"
        }
        
        response = requests.post(api_url, json=data, headers={"Content-Type": "application/json"})
        
        if response.status_code == 201:
            print(f"✅ API registration successful: {response.json()}")
        else:
            print(f"❌ API registration failed: {response.status_code} - {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Django server. Make sure it's running on port 8000.")
    except Exception as e:
        print(f"❌ API call failed: {str(e)}")

if __name__ == "__main__":
    test_email_verification()