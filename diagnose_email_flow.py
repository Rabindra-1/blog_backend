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

def diagnose_email_flow():
    print("=== Email Verification Flow Diagnosis ===")
    
    # Check current email settings
    print("\n--- Current Email Configuration ---")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'***SET***' if settings.EMAIL_HOST_PASSWORD and settings.EMAIL_HOST_PASSWORD != 'YOUR_NEW_APP_PASSWORD' else '***NOT SET***'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    # Check if App Password is configured
    if settings.EMAIL_HOST_PASSWORD == 'YOUR_NEW_APP_PASSWORD':
        print("\n❌ ISSUE FOUND: You haven't replaced 'YOUR_NEW_APP_PASSWORD' with your actual Gmail App Password!")
        print("📋 TO DO:")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("2. Generate a new App Password for 'Mail'")
        print("3. Update .env file: EMAIL_HOST_PASSWORD=your_actual_16_char_password")
        print("4. Restart Django server")
        return
    
    print("\n--- Testing Email Flow ---")
    
    # Create a test user with a different email
    test_email = "test.recipient@example.com"  # This is where the email SHOULD go
    test_username = "test_diagnosis"
    
    # Clean up any existing test user
    User.objects.filter(username=test_username).delete()
    
    # Create test user
    user = User.objects.create_user(
        username=test_username,
        email=test_email,  # User's signup email
        password="testpass123"
    )
    user.is_active = False
    user.save()
    
    print(f"\n📧 Created test user:")
    print(f"   Username: {user.username}")
    print(f"   Signup Email: {user.email}")
    print(f"   From Email: {settings.DEFAULT_FROM_EMAIL}")
    
    # Create and send verification
    verification = EmailVerification.objects.create(user=user)
    print(f"\n🔑 Generated verification token: {verification.token}")
    
    print(f"\n📤 Attempting to send email:")
    print(f"   FROM: {settings.DEFAULT_FROM_EMAIL} (Gmail SMTP sender)")
    print(f"   TO: {user.email} (User's signup email)")
    print(f"   Subject: Email Verification Code - Blog Platform")
    
    # This will show where the email is actually being sent
    verification.send_verification_email()
    
    print(f"\n✅ The email SHOULD be sent to: {user.email}")
    print(f"   NOT to: {settings.DEFAULT_FROM_EMAIL}")
    
    # Clean up
    user.delete()

if __name__ == "__main__":
    diagnose_email_flow()