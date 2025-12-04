from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['blog', 'author', 'content_preview', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['content', 'author__username', 'blog__title']
    actions = ['activate_comments', 'deactivate_comments']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def activate_comments(self, request, queryset):
        queryset.update(is_active=True)
    activate_comments.short_description = 'Activate selected comments'
    
    def deactivate_comments(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_comments.short_description = 'Deactivate selected comments'
