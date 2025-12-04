from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import uuid
import secrets

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=8, unique=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.token:
            # Generate a 6-digit numeric token for easy manual entry
            import random
            self.token = f"{random.randint(100000, 999999)}"
            # Ensure uniqueness
            while EmailVerification.objects.filter(token=self.token).exists():
                self.token = f"{random.randint(100000, 999999)}"
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)  # 15 minute expiration for manual entry
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()
    
    def send_verification_email(self):
        """Send verification email to user"""
        subject = 'Email Verification Code - Blog Platform'
        
        # Simple message focusing on the 6-digit code
        message = f'''
Hi {self.user.username},

Thank you for signing up for our Blog Platform!

Your email verification code is: {self.token}

Please enter this code in the verification form to activate your account.
This code will expire in 15 minutes.

If you didn't create an account, please ignore this email.

Best regards,
Blog Platform Team
'''
        
        try:
            # Try to send email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                fail_silently=False,
            )
            print(f"[SUCCESS] Email sent successfully to {self.user.email}")
        except Exception as e:
            print(f"[ERROR] Failed to send email to {self.user.email}: {str(e)}")
        
        # Always print to console for debugging (even in production)
        print(f"""\n{'='*60}
EMAIL VERIFICATION CODE
{'='*60}
To: {self.user.email}
Username: {self.user.username}
Verification Code: {self.token}
Expires: {self.expires_at.strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}\n""")
    
    def __str__(self):
        return f"Email verification for {self.user.username} - {'Used' if self.is_used else 'Pending'}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
