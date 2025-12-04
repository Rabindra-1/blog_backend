# Email Configuration Guide

## Current Issue
Your Django app is showing email verification in the console instead of sending actual emails because Gmail SMTP requires proper authentication.

## Solution: Gmail App Password Setup

### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account: https://myaccount.google.com/
2. Click on "Security" in the left sidebar
3. Under "Signing in to Google", enable "2-Step Verification" if not already enabled

### Step 2: Generate App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" as the app
3. Select "Other (custom name)" as the device
4. Enter "Django Blog App" as the name
5. Click "Generate"
6. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

### Step 3: Update Your .env File
Replace the current EMAIL_HOST_PASSWORD in your `.env` file:

```env
# Replace this line:
EMAIL_HOST_PASSWORD=52525&rahul

# With your new app password (remove spaces):
EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

### Step 4: Test Email Configuration

Run this Django management command to test:

```bash
cd backend
python manage.py shell
```

Then in the Django shell:

```python
from django.core.mail import send_mail
from django.conf import settings

# Test email sending
result = send_mail(
    'Test Email from Django',
    'This is a test email to verify SMTP configuration.',
    settings.DEFAULT_FROM_EMAIL,
    ['sahrabindra394@gmail.com'],  # Send to yourself for testing
    fail_silently=False,
)

print(f"Email sent successfully: {result}")
```

## Alternative Free Email Services

If Gmail doesn't work, here are other free options:

### Option 1: Outlook/Hotmail
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@outlook.com
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=your_email@outlook.com
```

### Option 2: Yahoo Mail
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@yahoo.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@yahoo.com
```

### Option 3: Mailtrap (Development Testing)
For development/testing only:
1. Sign up at https://mailtrap.io/ (free tier available)
2. Get SMTP credentials from your inbox
3. Update .env:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailtrap.io
EMAIL_PORT=2525
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_mailtrap_username
EMAIL_HOST_PASSWORD=your_mailtrap_password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

## Troubleshooting

### Common Issues:

1. **"Authentication failed"**
   - Make sure you're using an App Password, not your regular Gmail password
   - Verify 2FA is enabled on your Google account

2. **"Connection refused"**
   - Check if your firewall/antivirus is blocking port 587
   - Try port 465 with EMAIL_USE_SSL=True instead of EMAIL_USE_TLS=True

3. **"Less secure app access"**
   - This is no longer supported by Gmail
   - You MUST use App Passwords

### Debug Email Issues:

Add this to your Django settings for debugging:

```python
# In settings.py, add for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Testing Your Setup

Create a simple test view to verify email is working:

```python
# In any views.py file
from django.core.mail import send_mail
from django.http import JsonResponse

def test_email(request):
    try:
        send_mail(
            'Test Email',
            'If you receive this, email is working!',
            'sahrabindra394@gmail.com',
            ['sahrabindra394@gmail.com'],
            fail_silently=False,
        )
        return JsonResponse({'status': 'success', 'message': 'Email sent!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
```

Add to your urls.py:
```python
path('test-email/', test_email, name='test_email'),
```

Then visit: http://127.0.0.1:8000/test-email/

## Security Notes

1. **Never commit real passwords to version control**
2. **Use environment variables for all sensitive data**
3. **Consider using a dedicated email service for production** (SendGrid, Mailgun, etc.)
4. **App passwords are safer than regular passwords for SMTP**

## Production Recommendations

For production, consider using:
- **SendGrid** (free tier: 100 emails/day)
- **Mailgun** (free tier: 5,000 emails/month)
- **Amazon SES** (very cheap, pay-per-use)
- **Postmark** (free tier: 100 emails/month)

These services are more reliable and provide better deliverability than Gmail SMTP.