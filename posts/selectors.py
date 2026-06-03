from datetime import timedelta

from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from comments.models import Comment
from .models import Post, PostDailyMetric, PostPointAllocation


POST_LIST_TYPES = {
    'latest': {
        'title': _("Latest Posts"),
        'description': _("The newest published posts."),
    },
    'new': {
        'title': _("New Posts Today"),
        'description': _("Posts published today."),
    },
    'most_discussed': {
        'title': _("Most Discussed Posts"),
        'description': _("Posts with the most active discussion threads."),
    },
    'trending': {
        'title': _("Trending Posts"),
        'description': _("Posts with the most activity in the last 7 days."),
    },
    'recommended': {
        'title': _("Recommended Posts"),
        'description': _("Editorially recommended posts."),
    },
    'community_picks': {
        'title': _("Community Picks"),
        'description': _("Posts highlighted by the community and refined by editorial curation."),
    },
}


def get_community_picks_queryset(*, days=14):
    posts = Post.objects.filter(status='published', show_in_post_grids=True)
    today = timezone.localdate()
    date_from = today - timedelta(days=max(days - 1, 0))
    recent_points = PostPointAllocation.objects.filter(
        post=OuterRef('pk'),
        date__gte=date_from,
        date__lte=today,
    ).order_by().values('post').annotate(total=Sum('points')).values('total')[:1]

    return (
        posts.annotate(
            recent_points=Coalesce(
                Subquery(recent_points, output_field=IntegerField()),
                Value(0),
            ),
        ).annotate(
            community_score=(
                F('recent_points') * Value(100, output_field=IntegerField())
                + F('editor_rating')
            )
        ).filter(
            Q(recent_points__gt=0) | Q(editor_rating__gt=0)
        ).order_by('-community_score', '-recent_points', '-editor_rating', '-published_date')
    )


def get_posts_for_list_type(list_type=None):
    posts = Post.objects.filter(status='published')

    if list_type == 'new':
        today = timezone.localdate()
        return posts.filter(published_date__date=today).order_by('-published_date')

    if list_type == 'most_discussed':
        return posts.annotate(
            debate_threads=Count(
                'comments',
                filter=Q(
                    comments__is_approved=True,
                    comments__parent__isnull=True,
                    comments__children__is_approved=True,
                ),
                distinct=True,
            ),
            debate_replies=Count(
                'comments',
                filter=Q(comments__is_approved=True, comments__parent__isnull=False),
            ),
        ).filter(debate_threads__gt=0).order_by('-debate_threads', '-debate_replies', '-published_date')

    if list_type == 'trending':
        trend_start = timezone.localdate() - timedelta(days=7)
        recent_views = PostDailyMetric.objects.filter(
            post=OuterRef('pk'),
            date__gte=trend_start,
        ).order_by().values('post').annotate(total=Sum('views_count')).values('total')[:1]
        recent_comments = Comment.objects.filter(
            post=OuterRef('pk'),
            is_approved=True,
            created_at__date__gte=trend_start,
        ).order_by().values('post').annotate(total=Count('pk')).values('total')[:1]
        recent_debate_replies = Comment.objects.filter(
            post=OuterRef('pk'),
            is_approved=True,
            parent__isnull=False,
            created_at__date__gte=trend_start,
        ).order_by().values('post').annotate(total=Count('pk')).values('total')[:1]

        return posts.annotate(
            recent_views=Coalesce(
                Subquery(recent_views, output_field=IntegerField()),
                Value(0),
            ),
            recent_comments=Coalesce(
                Subquery(recent_comments, output_field=IntegerField()),
                Value(0),
            ),
            recent_debate_replies=Coalesce(
                Subquery(recent_debate_replies, output_field=IntegerField()),
                Value(0),
            ),
        ).annotate(
            trend_score=(
                F('recent_views')
                + F('recent_comments') * Value(3, output_field=IntegerField())
                + F('recent_debate_replies') * Value(2, output_field=IntegerField())
            )
        ).filter(trend_score__gt=0).order_by('-trend_score', '-published_date')

    if list_type == 'recommended':
        return posts.filter(editor_rating__gt=0).order_by('-editor_rating', '-published_date')

    if list_type == 'community_picks':
        return get_community_picks_queryset()

    return posts.order_by('-published_date')
