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
from django.core.mail import send_mail

def test_complete_email_flow():
    print("=== Complete Email Verification Test ===")
    
    # Step 1: Check email configuration
    print("\n--- Step 1: Email Configuration Check ---")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    
    # Check if app password is set
    if not settings.EMAIL_HOST_PASSWORD or settings.EMAIL_HOST_PASSWORD == 'YOUR_NEW_APP_PASSWORD':
        print("[ERROR] EMAIL_HOST_PASSWORD: Not properly configured")
        print("\nAction Required:")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("2. Sign in to suppotr.tech@gmail.com")
        print("3. Create App Password for 'Mail'")
        print("4. Update .env: EMAIL_HOST_PASSWORD=your_16_char_password")
        return
    else:
        print(f"[SUCCESS] EMAIL_HOST_PASSWORD: Configured ({len(settings.EMAIL_HOST_PASSWORD)} chars)")
    
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    # Step 2: Test basic email sending
    print("\n--- Step 2: Basic Email Test ---")
    test_recipient = input("Enter test email address (where you want to receive the test): ").strip()
    if not test_recipient:
        test_recipient = "suppotr.tech@gmail.com"  # Default for testing
    
    try:
        result = send_mail(
            'Test Email - Django Blog Platform',
            f'This is a test email to verify Gmail SMTP is working.\n\nFrom: {settings.DEFAULT_FROM_EMAIL}\nTo: {test_recipient}',
            settings.DEFAULT_FROM_EMAIL,
            [test_recipient],
            fail_silently=False,
        )
        print(f"[SUCCESS] Basic email test successful! Sent to: {test_recipient}")
        print("   Check your inbox for the test email.")
    except Exception as e:
        print(f"[ERROR] Basic email test failed: {str(e)}")
        if "Application-specific password required" in str(e):
            print("\nSolution: Update your Gmail App Password in .env file")
        return
    
    # Step 3: Test user registration email flow
    print("\n--- Step 3: User Registration Email Flow ---")
    
    # Create test user with the email address where you want to receive verification
    test_username = f"testuser_{int(__import__('time').time())}"
    
    print(f"Creating test user:")
    print(f"  Username: {test_username}")
    print(f"  Email: {test_recipient} (This is where verification email will be sent)")
    
    try:
        # Clean up any existing user
        User.objects.filter(username=test_username).delete()
        
        # Create user
        user = User.objects.create_user(
            username=test_username,
            email=test_recipient,  # User's signup email
            password="testpass123"
        )
        user.is_active = False
        user.save()
        
        # Create and send verification
        verification = EmailVerification.objects.create(user=user)
        print(f"\nEmail Details:")
        print(f"  FROM: {settings.DEFAULT_FROM_EMAIL}")
        print(f"  TO: {user.email}")
        print(f"  Verification Code: {verification.token}")
        
        # Send verification email
        verification.send_verification_email()
        
        print(f"\n[SUCCESS] Registration email flow completed!")
        print(f"Check your inbox at: {test_recipient}")
        print(f"Verification code: {verification.token}")
        
        # Clean up
        user.delete()
        
    except Exception as e:
        print(f"[ERROR] Registration email flow failed: {str(e)}")

if __name__ == "__main__":
    test_complete_email_flow()