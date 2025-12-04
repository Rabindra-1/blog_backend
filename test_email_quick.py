#!/usr/bin/env python
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    print("Testing email with new App Password...")
    print(f"Email Host: {settings.EMAIL_HOST}")
    print(f"Email User: {settings.EMAIL_HOST_USER}")
    print(f"Email Backend: {settings.EMAIL_BACKEND}")
    
    try:
        result = send_mail(
            'Test Email - New App Password',
            'This is a test email to verify the new App Password is working correctly.',
            settings.DEFAULT_FROM_EMAIL,
            ['suppotr.tech@gmail.com'],
            fail_silently=False,
        )
        
        if result == 1:
            print("✅ Email sent successfully! Check your inbox.")
        else:
            print("❌ Email sending failed.")
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")

if __name__ == "__main__":
    test_email()