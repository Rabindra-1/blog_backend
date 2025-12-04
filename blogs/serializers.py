from rest_framework import serializers
from .models import Blog, Tag, BlogImage, BlogVideo, BlogLike, BlogBookmark, Category
from accounts.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'color']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class BlogImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogImage
        fields = ['id', 'image', 'caption', 'order']

class BlogVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogVideo
        fields = ['id', 'video', 'thumbnail', 'caption', 'order']

class BlogListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = [
            'id', 'title', 'slug', 'content', 'author', 'category', 'tags', 
            'layout_type', 'featured_image', 'created_at', 'updated_at',
            'likes_count', 'views_count', 'is_liked', 'is_bookmarked', 'comments_count'
        ]
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False
    
    def get_comments_count(self, obj):
        return obj.comments.filter(is_active=True).count()

class BlogDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = BlogImageSerializer(many=True, read_only=True)
    videos = BlogVideoSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = [
            'id', 'title', 'slug', 'content', 'author', 'category', 'tags', 
            'layout_type', 'featured_image', 'images', 'videos', 'created_at', 'updated_at',
            'likes_count', 'views_count', 'is_liked', 'is_bookmarked', 'comments_count'
        ]
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(user=request.user).exists()
        return False
    
    def get_comments_count(self, obj):
        return obj.comments.filter(is_active=True).count()

class BlogCreateUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    category = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Blog
        fields = [
            'title', 'content', 'category', 'layout_type', 'featured_image', 'tags', 'is_published'
        ]
    
    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        category_name = validated_data.pop('category', None)
        
        # Handle category - create if it doesn't exist
        if category_name:
            from .models import Category
            category, created = Category.objects.get_or_create(
                name=category_name.title(),
                defaults={'description': f'{category_name.title()} category'}
            )
            validated_data['category'] = category
        
        blog = Blog.objects.create(**validated_data)
        
        # Handle tags
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_name.lower())
            blog.tags.add(tag)
        
        return blog
    
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        category_name = validated_data.pop('category', None)
        
        # Handle category - create if it doesn't exist
        if category_name:
            from .models import Category
            category, created = Category.objects.get_or_create(
                name=category_name.title(),
                defaults={'description': f'{category_name.title()} category'}
            )
            validated_data['category'] = category
        
        # Update blog fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if tags_data is not None:
            instance.tags.clear()
            for tag_name in tags_data:
                tag, created = Tag.objects.get_or_create(name=tag_name.lower())
                instance.tags.add(tag)
        
        return instance
