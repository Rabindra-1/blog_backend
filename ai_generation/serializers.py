from rest_framework import serializers
from .models import GeneratedContent, ImageGeneration
from accounts.serializers import UserSerializer

class GeneratedContentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'user', 'content_type', 'prompt', 'result', 
            'file_path', 'metadata', 'created_at', 'processing_time',
            'success', 'error_message'
        ]
        read_only_fields = ['id', 'user', 'created_at']

class ImageGenerationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ImageGeneration
        fields = [
            'id', 'user', 'uploaded_image', 'image_url', 'analysis_type', 
            'generated_text', 'local_path', 'width', 'height', 'created_at', 
            'success', 'error_message'
        ]
        read_only_fields = ['id', 'user', 'created_at']
