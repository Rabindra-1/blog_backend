from django.urls import path
from . import views

urlpatterns = [
    path('', views.BlogListCreateView.as_view(), name='blog_list_create'),
    # Specific paths first to avoid being caught by slug pattern
    path('my-blogs/', views.my_blogs, name='my_blogs'),
    path('bookmarked/', views.bookmarked_blogs, name='bookmarked_blogs'),
    path('generate/', views.generate_blog_content, name='generate_blog_content'),
    path('generate-from-video/', views.generate_blog_from_video, name='generate_blog_from_video'),
    path('tags/', views.tags, name='tags'),
    path('categories/', views.categories, name='categories'),
    path('<int:blog_id>/like/', views.like_blog, name='like_blog'),
    path('<int:blog_id>/bookmark/', views.bookmark_blog, name='bookmark_blog'),
    path('<int:blog_id>/images/', views.add_blog_image, name='add_blog_image'),
    path('<int:blog_id>/videos/', views.add_blog_video, name='add_blog_video'),
    path('images/<int:image_id>/', views.delete_blog_image, name='delete_blog_image'),
    path('videos/<int:video_id>/', views.delete_blog_video, name='delete_blog_video'),
    # Slug pattern last to catch any remaining paths
    path('<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),
]
