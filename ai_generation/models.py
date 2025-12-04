from django.db import models
from django.contrib.auth.models import User

class GeneratedContent(models.Model):
    CONTENT_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('youtube', 'YouTube Processing'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_content')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    prompt = models.TextField()
    result = models.TextField(blank=True)
    file_path = models.CharField(max_length=500, blank=True)  # For images/videos
    metadata = models.JSONField(default=dict, blank=True)  # Additional data
    created_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(null=True, blank=True)  # In seconds
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.content_type} - {self.created_at}"

class ImageGeneration(models.Model):
    ANALYSIS_CHOICES = [
        ('description', 'General Description'),
        ('detailed', 'Detailed Analysis'),
        ('caption', 'Caption'),
        ('ocr', 'Text Extraction (OCR)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='image_analyses')
    uploaded_image = models.ImageField(upload_to='uploaded_images/', null=True, blank=True)
    image_url = models.URLField(blank=True, help_text="URL of image to analyze (if not uploading file)")
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_CHOICES, default='description')
    generated_text = models.TextField(blank=True, help_text="AI-generated description of the image")
    local_path = models.CharField(max_length=500, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Image analysis by {self.user.username} - {self.analysis_type}"
