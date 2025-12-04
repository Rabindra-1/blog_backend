from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')  # Default blue color
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Blog(models.Model):
    LAYOUT_CHOICES = [
        ('image-left', 'Image Left'),
        ('image-right', 'Image Right'),
        ('gallery', 'Gallery'),
        ('minimal', 'Minimal'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='blogs')
    tags = models.ManyToManyField(Tag, blank=True, related_name='blogs')
    layout_type = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='minimal')
    featured_image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

class BlogImage(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='blog_images/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.blog.title} - Image {self.order}"

class BlogVideo(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='blog_videos/')
    thumbnail = models.ImageField(upload_to='blog_video_thumbnails/', null=True, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.blog.title} - Video {self.order}"

class BlogLike(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('blog', 'user')
    
    def __str__(self):
        return f"{self.user.username} likes {self.blog.title}"

class BlogBookmark(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarked_blogs')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('blog', 'user')
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.blog.title}"

class BlogView(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='blog_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='blog_views')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # For authenticated users: unique per user per blog
        # For anonymous users: unique per IP per blog
        constraints = [
            models.UniqueConstraint(
                fields=['blog', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_view_per_user_per_blog'
            ),
            models.UniqueConstraint(
                fields=['blog', 'ip_address'],
                condition=models.Q(user__isnull=True),
                name='unique_view_per_ip_per_blog'
            ),
        ]
        indexes = [
            models.Index(fields=['blog', 'user']),
            models.Index(fields=['blog', 'ip_address']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} viewed {self.blog.title}"
        return f"Anonymous ({self.ip_address}) viewed {self.blog.title}"
