from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test email to',
            default='sahrabindra394@gmail.com'
        )

    def handle(self, *args, **options):
        recipient = options['to']
        
        self.stdout.write(f"Testing email configuration...")
        self.stdout.write(f"Email Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Email Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"Email Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"Email User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"Default From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Sending test email to: {recipient}")
        self.stdout.write("-" * 50)

        try:
            result = send_mail(
                subject='Django Email Test - Blog Platform',
                message='''
Hello!

This is a test email from your Django Blog Platform.

If you're receiving this email, your email configuration is working correctly!

Email Configuration Details:
- Backend: {}
- Host: {}
- Port: {}
- TLS: {}

Best regards,
Django Blog Platform
                '''.format(
                    settings.EMAIL_BACKEND,
                    settings.EMAIL_HOST,
                    settings.EMAIL_PORT,
                    settings.EMAIL_USE_TLS
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Email sent successfully to {recipient}!')
                )
                self.stdout.write(
                    self.style.SUCCESS('Check your inbox (and spam folder) for the test email.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Email sending failed - no error but result was 0')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Email sending failed with error: {str(e)}')
            )
            
            # Provide helpful error messages
            error_str = str(e).lower()
            if 'authentication failed' in error_str:
                self.stdout.write(
                    self.style.WARNING('\n💡 Troubleshooting tip:')
                )
                self.stdout.write(
                    'Gmail requires an App Password, not your regular password.'
                )
                self.stdout.write(
                    'Generate one at: https://myaccount.google.com/apppasswords'
                )
            elif 'connection refused' in error_str:
                self.stdout.write(
                    self.style.WARNING('\n💡 Troubleshooting tip:')
                )
                self.stdout.write(
                    'Check your firewall settings and ensure port 587 is not blocked.'
                )
            elif 'timeout' in error_str:
                self.stdout.write(
                    self.style.WARNING('\n💡 Troubleshooting tip:')
                )
                self.stdout.write(
                    'Network timeout - check your internet connection and try again.'
                )
            
            self.stdout.write(
                self.style.WARNING('\nFor detailed setup instructions, see: backend/EMAIL_SETUP_GUIDE.md')
            )
            
            sys.exit(1)