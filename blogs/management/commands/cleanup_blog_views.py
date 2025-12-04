from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from blogs.models import BlogView, Blog


class Command(BaseCommand):
    help = 'Clean up old blog views and provide view analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Delete view records older than this many days (default: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--analytics',
            action='store_true',
            help='Show blog view analytics'
        )

    def handle(self, *args, **options):
        if options['analytics']:
            self.show_analytics()
        
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find old view records
        old_views = BlogView.objects.filter(created_at__lt=cutoff_date)
        count = old_views.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No blog views older than {days} days found.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} blog view records older than {days} days'
                )
            )
            return
        
        # Delete old records
        deleted_count, _ = old_views.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} blog view records older than {days} days'
            )
        )
    
    def show_analytics(self):
        """Display blog view analytics"""
        self.stdout.write(self.style.SUCCESS('=== Blog View Analytics ==='))
        
        # Total views
        total_views = BlogView.objects.count()
        self.stdout.write(f'Total unique views: {total_views}')
        
        # Views by authentication status
        auth_views = BlogView.objects.filter(user__isnull=False).count()
        anon_views = BlogView.objects.filter(user__isnull=True).count()
        
        self.stdout.write(f'Authenticated user views: {auth_views}')
        self.stdout.write(f'Anonymous views: {anon_views}')
        
        # Top viewed blogs
        self.stdout.write('\n=== Top 10 Most Viewed Blogs ===')
        top_blogs = Blog.objects.filter(is_published=True).order_by('-views_count')[:10]
        
        for i, blog in enumerate(top_blogs, 1):
            self.stdout.write(f'{i}. "{blog.title}" - {blog.views_count} views')
        
        # Recent activity (last 7 days)
        recent_date = timezone.now() - timedelta(days=7)
        recent_views = BlogView.objects.filter(created_at__gte=recent_date).count()
        
        self.stdout.write(f'\nViews in the last 7 days: {recent_views}')