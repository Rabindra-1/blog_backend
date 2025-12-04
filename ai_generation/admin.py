from django.contrib import admin
from .models import GeneratedContent, ImageGeneration

@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'prompt', 'success', 'created_at', 'processing_time']
    list_filter = ['content_type', 'success', 'created_at']
    search_fields = ['user__username', 'prompt', 'result']
    readonly_fields = ['created_at', 'processing_time']
    raw_id_fields = ['user']

@admin.register(ImageGeneration)
class ImageGenerationAdmin(admin.ModelAdmin):
    list_display = ['user', 'analysis_type', 'success', 'created_at']
    list_filter = ['analysis_type', 'success', 'created_at']
    search_fields = ['user__username', 'generated_text']
    readonly_fields = ['created_at']
    raw_id_fields = ['user']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
