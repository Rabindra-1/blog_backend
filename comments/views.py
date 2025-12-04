from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Comment
from .serializers import CommentSerializer, CommentCreateSerializer
from blogs.models import Blog

class CommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        blog_id = self.kwargs.get('blog_id')
        return Comment.objects.filter(
            blog_id=blog_id, 
            is_active=True, 
            parent__isnull=True  # Only top-level comments
        ).order_by('created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            blog_id = self.kwargs.get('blog_id')
            blog = get_object_or_404(Blog, id=blog_id, is_published=True)
            context['blog'] = blog
        return context
    
    def perform_create(self, serializer):
        blog_id = self.kwargs.get('blog_id')
        blog = get_object_or_404(Blog, id=blog_id, is_published=True)
        serializer.save(author=self.request.user, blog=blog)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_update(self, serializer):
        # Only allow author to update
        if serializer.instance.author != self.request.user:
            raise PermissionError("You can only edit your own comments.")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only allow author to delete (soft delete)
        if instance.author != self.request.user:
            raise PermissionError("You can only delete your own comments.")
        instance.is_active = False
        instance.save()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reply_to_comment(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id, is_active=True)
    
    data = request.data.copy()
    data['blog'] = parent_comment.blog.id
    data['parent'] = parent_comment.id
    
    serializer = CommentCreateSerializer(data=data)
    if serializer.is_valid():
        serializer.save(author=request.user, blog=parent_comment.blog)
        return Response(CommentSerializer(serializer.instance, context={'request': request}).data, 
                       status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
