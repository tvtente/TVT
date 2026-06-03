# widgets/signals.py
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from books.models import Book
from posts.models import Post, PostFavorite, PostPointAllocation
from publications.models import Publication
from widgets.cache_keys import widget_cache_keys_for_widget
from widgets.models import Widget
from widgets.selectors import POST_WIDGET_TYPES


POINT_WIDGET_TYPES = {
    Widget.WidgetType.POST_GRID_TOP_RATED_TODAY,
    Widget.WidgetType.POST_GRID_TOP_RATED_WEEK,
    Widget.WidgetType.POST_GRID_COMMUNITY_PICKS,
}

FAVORITE_WIDGET_TYPES = {
    Widget.WidgetType.POST_GRID_MOST_FAVORITED,
}

POST_CONTENT_WIDGET_TYPES = POST_WIDGET_TYPES | {
    Widget.WidgetType.BLOG_CATEGORIES,
    Widget.WidgetType.FEATURED_TAGS,
}

BOOK_WIDGET_TYPES = {
    Widget.WidgetType.BOOK_GRID_RECENT,
}

PUBLICATION_WIDGET_TYPES = {
    Widget.WidgetType.PUBLICATION_GRID_RECENT,
}


def clear_widget_cache(widget_id, zone_slug):
    for cache_key in widget_cache_keys_for_widget(widget_id, zone_slug):
        cache.delete(cache_key)


def clear_widgets_by_types(widget_types):
    if not widget_types:
        return

    widgets = (
        Widget.objects.filter(widget_type__in=widget_types)
        .select_related("zone")
    )
    for widget in widgets:
        zone_slug = widget.zone.slug if widget.zone_id and widget.zone else ""
        clear_widget_cache(widget.id, zone_slug)


def clear_all_widget_caches():
    widgets = Widget.objects.all().select_related("zone")
    for widget in widgets:
        zone_slug = widget.zone.slug if widget.zone_id and widget.zone else ""
        clear_widget_cache(widget.id, zone_slug)


@receiver(pre_save, sender=Widget)
def remember_previous_widget_zone(sender, instance, **kwargs):
    instance._previous_zone_slug = None
    if not instance.pk:
        return

    instance._previous_zone_slug = (
        Widget.objects.filter(pk=instance.pk)
        .values_list("zone__slug", flat=True)
        .first()
    )


@receiver([post_save, post_delete], sender=Widget)
def on_widget_change(sender, instance, **kwargs):
    clear_widget_cache(
        instance.id,
        getattr(instance, "_previous_zone_slug", None) or "",
    )
    zone_slug = instance.zone.slug if instance.zone_id and instance.zone else ""
    if zone_slug != getattr(instance, "_previous_zone_slug", None):
        clear_widget_cache(instance.id, zone_slug)


@receiver([post_save, post_delete], sender=Post)
def on_post_change(sender, instance, **kwargs):
    clear_widgets_by_types(POST_CONTENT_WIDGET_TYPES)


@receiver([post_save, post_delete], sender=PostPointAllocation)
def on_post_points_change(sender, instance, **kwargs):
    clear_widgets_by_types(POINT_WIDGET_TYPES)


@receiver([post_save, post_delete], sender=PostFavorite)
def on_post_favorite_change(sender, instance, **kwargs):
    clear_widgets_by_types(FAVORITE_WIDGET_TYPES)


@receiver([post_save, post_delete], sender=Book)
def on_book_change(sender, instance, **kwargs):
    clear_widgets_by_types(BOOK_WIDGET_TYPES)


@receiver([post_save, post_delete], sender=Publication)
def on_publication_change(sender, instance, **kwargs):
    clear_widgets_by_types(PUBLICATION_WIDGET_TYPES)
