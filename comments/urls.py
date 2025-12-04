from django.urls import path
from . import views

urlpatterns = [
    path('blog/<int:blog_id>/', views.CommentListCreateView.as_view(), name='comment_list_create'),
    path('<int:pk>/', views.CommentDetailView.as_view(), name='comment_detail'),
    path('<int:comment_id>/reply/', views.reply_to_comment, name='reply_to_comment'),
]
