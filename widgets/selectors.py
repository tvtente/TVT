import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.db.models.functions import Length
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from accounts.models import User
from accounts.views import _profile_has_cv_in_language
from books.models import Book
from categories.models import Category
from posts.models import Post, PostPointAllocation
from posts.selectors import get_community_picks_queryset, get_published_posts_queryset
from publications.models import Publication
from pages.models import Page
from tags.models import Tag
from testimonials.models import Testimonial
from core.cache_observability import get_cache_logger, log_cache_event
from widgets.cache_keys import widget_items_cache_key
from widgets.models import Widget, WidgetZone


logger = logging.getLogger(__name__)
cache_logger = get_cache_logger("widgets")

REFLECTION_TAG_SLUGS = [
    "reflexion",
    "pensamiento",
    "cuestionamiento",
    "conciencia",
    "mente",
]
WELLBEING_TAG_SLUGS = [
    "bienestar",
    "salud-mental",
    "descanso",
    "habitos",
    "atencion",
    "estres",
]
FEATURED_TAG_SLUGS = [
    "psicologia",
    "bienestar",
    "inteligencia-artificial",
    "salud-mental",
    "pensamiento",
    "productividad",
    "atencion",
    "habitos",
]
POST_WIDGET_TYPES = {
    "recent_posts",
    "most_viewed_posts",
    "most_commented_posts",
    "editor_picks_posts",
    "post_grid_recent",
    "post_grid_category",
    "post_grid_popular",
    "post_grid_commented",
    "post_grid_editor",
    "post_grid_top_rated_today",
    "post_grid_top_rated_week",
    "post_grid_most_favorited",
    "post_grid_community_picks",
    "post_grid_top_tags",
    "post_intent_reflection",
    "post_intent_quick_reads",
    "post_intent_wellbeing",
    "post_intent_debate",
    "post_carousel",
    "post_carousel_commented",
    "post_carousel_viewed",
    "hero_carousel",
}

LANDSCAPE_WIDGET_TYPES = {
    "post_grid_recent",
    "post_grid_category",
    "post_grid_popular",
    "post_grid_commented",
    "post_grid_editor",
    "post_grid_top_rated_today",
    "post_grid_top_rated_week",
    "post_grid_most_favorited",
    "post_grid_community_picks",
    "post_grid_top_tags",
    "post_intent_reflection",
    "post_intent_quick_reads",
    "post_intent_wellbeing",
    "post_intent_debate",
    "post_carousel",
    "post_carousel_commented",
    "post_carousel_viewed",
    "hero_carousel",
    "publication_grid_recent",
}

SQUARE_WIDGET_TYPES = {
    "book_grid_recent",
}


def _get_thumbnail_data(obj):
    if isinstance(obj, Post):
        thumbnail_image = obj.get_mobile_image()
        if thumbnail_image:
            return thumbnail_image.url, "mobile"
        thumbnail_image = obj.get_social_image()
        if thumbnail_image:
            return thumbnail_image.url, "social"
        thumbnail_image = obj.get_featured_image()
        if thumbnail_image:
            return thumbnail_image.url, "featured"
    return "", ""


def _call_image_getter(obj, getter_name):
    getter = getattr(obj, getter_name, None)
    if callable(getter):
        return getter()
    return None


def _get_square_image(obj):
    return _call_image_getter(obj, "get_social_image")


def _get_landscape_image(obj):
    return _call_image_getter(obj, "get_featured_image") or _call_image_getter(
        obj,
        "get_cover_image",
    )


def _get_mobile_image(obj):
    return _call_image_getter(obj, "get_mobile_image")


def get_widget_image_format(widget_instance, zone_slug):
    if widget_instance.image_format != Widget.ImageFormat.AUTO:
        return widget_instance.image_format

    if widget_instance.widget_type in SQUARE_WIDGET_TYPES:
        return Widget.ImageFormat.SQUARE

    if zone_slug.endswith("sidebar-right"):
        return Widget.ImageFormat.SQUARE

    if widget_instance.widget_type in LANDSCAPE_WIDGET_TYPES:
        return Widget.ImageFormat.LANDSCAPE

    return Widget.ImageFormat.LANDSCAPE


def _resolve_display_image(obj, image_format):
    if image_format == Widget.ImageFormat.MOBILE:
        return _get_mobile_image(obj) or _get_landscape_image(obj) or _get_square_image(obj)
    if image_format == Widget.ImageFormat.SQUARE:
        return _get_square_image(obj) or _get_landscape_image(obj)
    return _get_landscape_image(obj) or _get_square_image(obj)


def _with_featured_image(queryset, language_code):
    asset_q = Q(
        translations__language_code=language_code,
        translations__featured_image_asset__isnull=False,
        translations__featured_image_asset__image__isnull=False,
    ) & ~Q(translations__featured_image_asset__image="")
    return queryset.filter(asset_q).distinct()


def _grid_visible_posts(language_code=None):
    return get_published_posts_queryset(language_code).filter(show_in_post_grids=True)


def _published_books_queryset(language_code):
    return (
        Book.objects.language(language_code)
        .filter(is_published=True, translations__language_code=language_code)
        .prefetch_related("authors", "categories")
        .order_by("-publication_date", "-created_at")
        .distinct()
    )


def _published_publications_queryset(language_code):
    return (
        Publication.objects.language(language_code)
        .filter(is_published=True, translations__language_code=language_code)
        .prefetch_related("authors", "categories")
        .order_by("-publication_date", "-created_at")
        .distinct()
    )


def _top_rated_posts_queryset(language_code, *, days=1):
    today = timezone.localdate()
    date_from = today - timezone.timedelta(days=max(days - 1, 0))
    point_filter = Q(point_allocations__date__gte=date_from, point_allocations__date__lte=today)

    return (
        _grid_visible_posts(language_code)
        .annotate(
            total_points=Sum(
                "point_allocations__points",
                filter=point_filter,
            )
        )
        .filter(total_points__gt=0)
        .order_by("-total_points", "-published_date")
    )


def _most_favorited_posts_queryset(language_code=None):
    return (
        _grid_visible_posts(language_code)
        .annotate(total_favorites=Count("favorites", distinct=True))
        .filter(total_favorites__gt=0)
        .order_by("-total_favorites", "-published_date")
    )


def _build_widget_items(widget_instance, language_code, *, category=None):
    match widget_instance.widget_type:
        case "recent_posts":
            return list(
                get_published_posts_queryset(language_code).order_by("-published_date")[
                    :widget_instance.item_count
                ]
            )

        case "most_viewed_posts":
            return list(
                get_published_posts_queryset(language_code)
                .order_by("-views_count", "-published_date")[: widget_instance.item_count]
            )

        case "most_commented_posts":
            items_qs = (
                get_published_posts_queryset(language_code)
                .annotate(
                    num_comments=Count(
                        "comments",
                        filter=Q(comments__is_approved=True),
                    )
                )
                .filter(num_comments__gt=0)
                .order_by("-num_comments", "-published_date")
            )
            return list(items_qs[: widget_instance.item_count])

        case "editor_picks_posts":
            return list(
                get_published_posts_queryset(language_code).filter(editor_rating__gt=0)
                .order_by("-editor_rating", "-published_date")[: widget_instance.item_count]
            )

        case "blog_categories":
            categories_qs = (
                Category.objects.language(language_code)
                .filter(translations__language_code=language_code)
                .annotate(
                    num_posts=Count(
                        "posts_posts",
                        filter=Q(posts_posts__status="published"),
                        distinct=True,
                    )
                )
                .filter(num_posts__gt=0)
                .order_by("-num_posts", "translations__name")
                .distinct()
            )
            return list(categories_qs[: widget_instance.item_count])

        case "featured_tags":
            tags_queryset = (
                Tag.objects.language(language_code)
                .filter(translations__language_code=language_code)
                .annotate(
                    num_posts=Count(
                        "post_links",
                        filter=Q(
                            post_links__post__status="published",
                            post_links__language=language_code,
                            post_links__post__translations__language_code=language_code,
                        ),
                        distinct=True,
                    )
                )
                .annotate(
                    recent_clicks=Sum(
                        "daily_metrics__click_count",
                        filter=Q(
                            daily_metrics__date__gte=timezone.localdate()
                            - timezone.timedelta(days=30)
                        ),
                    )
                )
                .filter(num_posts__gt=0)
                .distinct()
            )
            curated_tags = list(tags_queryset.filter(slug__in=FEATURED_TAG_SLUGS))
            # Do not leave the cloud empty merely because the editorial preset
            # has no matching published posts after curation or archiving.
            tags = curated_tags or list(tags_queryset.order_by("-num_posts", "translations__label"))
            tag_order = {
                slug: index for index, slug in enumerate(FEATURED_TAG_SLUGS)
            }
            return sorted(
                tags,
                key=lambda tag: (
                    -(tag.recent_clicks or 0),
                    -tag.click_count,
                    -tag.num_posts,
                    tag_order.get(tag.slug, len(tag_order)),
                ),
            )[: widget_instance.item_count]

        case "category_tag_cloud":
            # This cloud belongs to a concrete post context.  Returning no
            # items outside a post keeps it out of generic blog sidebars.
            if category is None:
                return []

            category_tree = category.get_descendants(include_self=True)
            tags_queryset = (
                Tag.objects.language(language_code)
                .filter(
                    translations__language_code=language_code,
                    post_links__language=language_code,
                    post_links__post__status="published",
                    post_links__post__translations__language_code=language_code,
                    post_links__post__categories__in=category_tree,
                )
                .annotate(
                    num_posts=Count("post_links__post", distinct=True),
                    recent_clicks=Sum(
                        "daily_metrics__click_count",
                        filter=Q(
                            daily_metrics__date__gte=timezone.localdate()
                            - timezone.timedelta(days=30)
                        ),
                    ),
                )
                .filter(num_posts__gt=0)
                .order_by("-recent_clicks", "-click_count", "-num_posts", "translations__label")
                .distinct()
            )
            tags = list(tags_queryset[: widget_instance.item_count])

            # A continuous scale makes frequent tags more prominent without
            # concealing the less common but still relevant ones.
            weights = [
                max(tag.recent_clicks or 0, tag.click_count or 0, tag.num_posts or 0)
                for tag in tags
            ]
            smallest, largest = (min(weights), max(weights)) if weights else (0, 0)
            for tag, weight in zip(tags, weights):
                ratio = 0.5 if smallest == largest else (weight - smallest) / (largest - smallest)
                tag.cloud_font_size = round(0.82 + (ratio * 0.52), 2)
            return tags

        case "post_grid_recent":
            items_qs = _with_featured_image(
                _grid_visible_posts(language_code).order_by("-published_date"),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_category":
            items_qs = _grid_visible_posts(language_code)
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            else:
                logger.warning(
                    "Widget '%s' is Post Grid: Category but has no category selected.",
                    widget_instance.title,
                )
                items_qs = Post.objects.none()
            items_qs = _with_featured_image(
                items_qs.order_by("-published_date"),
                language_code,
            )
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "post_grid_popular":
            items_qs = _with_featured_image(
                _grid_visible_posts(language_code).order_by("-views_count", "-published_date"),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_commented":
            items_qs = (
                _grid_visible_posts(language_code)
                .annotate(
                    num_comments=Count(
                        "comments",
                        filter=Q(comments__is_approved=True),
                    )
                )
                .filter(num_comments__gt=0)
                .order_by("-num_comments", "-published_date")
            )
            items_qs = _with_featured_image(items_qs, language_code)
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_editor":
            # Editorially rated posts remain useful even when no featured
            # image has been uploaded.  The grid template already renders a
            # complete card without an image, so do not hide them here.
            items_qs = (
                _grid_visible_posts(language_code)
                .filter(editor_rating__gt=0)
                .order_by("-editor_rating", "-published_date")
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_top_rated_today":
            items_qs = _with_featured_image(
                _top_rated_posts_queryset(language_code, days=1),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_top_rated_week":
            items_qs = _with_featured_image(
                _top_rated_posts_queryset(language_code, days=7),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_most_favorited":
            items_qs = _with_featured_image(
                _most_favorited_posts_queryset(language_code),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_community_picks":
            items_qs = _with_featured_image(
                get_community_picks_queryset(language_code=language_code),
                language_code,
            )
            return list(items_qs[: widget_instance.item_count])

        case "post_grid_top_tags":
            # In the homepage sidebar these tags act as a discovery aid for the
            # editorially important content.  Rank tags attached to rated or
            # commented posts before generic click-volume tags, so an unrelated
            # historic topic does not dominate this widget.
            tag_queryset = (
                Tag.objects.language(language_code)
                .filter(translations__language_code=language_code)
                .annotate(
                    num_posts=Count(
                        "post_links",
                        filter=Q(
                            post_links__post__status="published",
                            post_links__language=language_code,
                            post_links__post__translations__language_code=language_code,
                        ),
                        distinct=True,
                    ),
                    recent_clicks=Sum(
                        "daily_metrics__click_count",
                        filter=Q(
                            daily_metrics__date__gte=timezone.localdate()
                            - timezone.timedelta(days=30)
                        ),
                    ),
                    rated_posts=Count(
                        "post_links",
                        filter=Q(
                            post_links__post__status="published",
                            post_links__language=language_code,
                            post_links__post__translations__language_code=language_code,
                            post_links__post__editor_rating__gt=0,
                        ),
                        distinct=True,
                    ),
                    commented_posts=Count(
                        "post_links__post",
                        filter=Q(
                            post_links__post__status="published",
                            post_links__language=language_code,
                            post_links__post__translations__language_code=language_code,
                            post_links__post__comments__is_approved=True,
                        ),
                        distinct=True,
                    ),
                )
                .filter(num_posts__gt=0)
                .order_by(
                    "-rated_posts",
                    "-commented_posts",
                    "-recent_clicks",
                    "-click_count",
                    "-num_posts",
                )
                .distinct()
            )
            top_tags = list(tag_queryset[: widget_instance.top_tag_count])
            items_qs = get_published_posts_queryset(language_code).filter(
                tag_links__tag__in=top_tags,
                tag_links__language=language_code,
            )
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(
                items_qs.distinct().order_by("-published_date")[: widget_instance.item_count]
            )

        case "post_intent_reflection":
            items_qs = get_published_posts_queryset(language_code).filter(
                tags__slug__in=REFLECTION_TAG_SLUGS,
            ).order_by("-editor_rating", "-published_date")
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            items_qs = _with_featured_image(items_qs, language_code)
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "post_intent_quick_reads":
            items_qs = (
                get_published_posts_queryset(language_code)
                .exclude(translations__summary="")
                .annotate(content_length=Length("translations__content"))
                .filter(content_length__lte=1800)
                .order_by("-published_date")
            )
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            items_qs = _with_featured_image(items_qs, language_code)
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "post_intent_wellbeing":
            items_qs = get_published_posts_queryset(language_code).filter(
                tags__slug__in=WELLBEING_TAG_SLUGS,
            ).order_by("-editor_rating", "-published_date")
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            items_qs = _with_featured_image(items_qs, language_code)
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "post_intent_debate":
            items_qs = (
                get_published_posts_queryset(language_code)
                .annotate(
                    num_comments=Count(
                        "comments",
                        filter=Q(comments__is_approved=True),
                    )
                )
                .filter(num_comments__gt=0)
                .order_by("-num_comments", "-published_date")
            )
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            items_qs = _with_featured_image(items_qs, language_code)
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "post_carousel":
            items_qs = get_published_posts_queryset(language_code)
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(
                items_qs.order_by("-editor_rating", "-published_date")[
                    : widget_instance.item_count
                ]
            )

        case "post_carousel_commented":
            items_qs = (
                get_published_posts_queryset(language_code)
                .annotate(
                    num_comments=Count(
                        "comments",
                        filter=Q(comments__is_approved=True),
                    )
                )
                .filter(num_comments__gt=0)
                .order_by("-num_comments", "-published_date")
            )
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(items_qs[: widget_instance.item_count])

        case "post_carousel_viewed":
            items_qs = get_published_posts_queryset(language_code).order_by(
                "-views_count",
                "-published_date",
            )
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(items_qs[: widget_instance.item_count])

        case "hero_carousel":
            items_qs = _grid_visible_posts(language_code).order_by("-editor_rating", "-published_date")
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(items_qs.distinct()[: widget_instance.item_count])

        case "book_grid_recent":
            items_qs = _published_books_queryset(language_code)
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(items_qs[: widget_instance.item_count])

        case "page_card":
            if not widget_instance.page_filter_id:
                return []
            pages = list(
                Page.objects.language(language_code)
                .filter(
                    pk=widget_instance.page_filter_id,
                    status="published",
                    translations__language_code=language_code,
                )
                .select_related("author", "author__profile")
            )
            for page in pages:
                page.widget_destination_url = page.get_absolute_url()
                author_profile = getattr(page.author, "profile", None)
                if (
                    widget_instance.link_to_author_cv
                    and author_profile
                    and _profile_has_cv_in_language(author_profile, language_code)
                ):
                    with override(language_code):
                        page.widget_destination_url = reverse(
                            "accounts:public_profile",
                            kwargs={"username": page.author.username},
                        )
            return pages

        case "publication_grid_recent":
            items_qs = _published_publications_queryset(language_code)
            if widget_instance.category_filter:
                items_qs = items_qs.filter(categories=widget_instance.category_filter)
            return list(items_qs[: widget_instance.item_count])

        case "user_directory":
            return list(
                User.objects.filter(
                    is_active=True,
                    profile__is_trusted_commenter=True,
                )
                .select_related("profile")
                .order_by("username")[: widget_instance.item_count]
            )

        case "testimonials":
            return list(
                Testimonial.objects.filter(is_active=True).order_by("-created_at")[
                    : widget_instance.item_count
                ]
            )

        case _:
            logger.warning(
                "Unrecognized widget type '%s' for widget '%s'.",
                widget_instance.widget_type,
                widget_instance.title,
            )
            return []


def _decorate_widget_items(widget_instance, items, zone_slug):
    image_format = get_widget_image_format(widget_instance, zone_slug)

    if widget_instance.widget_type in POST_WIDGET_TYPES:
        for post_obj in items:
            post_obj.thumbnail_url, post_obj.thumbnail_kind = _get_thumbnail_data(post_obj)

    for item in items:
        item.widget_display_image = _resolve_display_image(item, image_format)
        item.widget_image_format = image_format

    return items


def get_widget_items(widget_instance, language_code, zone_slug, *, category=None):
    # A category cloud changes with the post being read.  Do not place it in
    # the generic widget cache, whose key deliberately has no post/category.
    if widget_instance.widget_type == Widget.WidgetType.CATEGORY_TAG_CLOUD:
        return _decorate_widget_items(
            widget_instance,
            _build_widget_items(widget_instance, language_code, category=category),
            zone_slug,
        )

    cache_key = widget_items_cache_key(widget_instance.id, language_code, zone_slug)

    if widget_instance.cache_timeout > 0:
        cached_items = cache.get(cache_key)
        if cached_items is not None:
            log_cache_event(
                cache_logger,
                component="widget_items",
                action="hit",
                cache_key=cache_key,
                language_code=language_code,
                timeout=widget_instance.cache_timeout,
                detail=f"widget_id={widget_instance.id}",
            )
            return cached_items

    if widget_instance.cache_timeout > 0:
        log_cache_event(
            cache_logger,
            component="widget_items",
            action="miss",
            cache_key=cache_key,
            language_code=language_code,
            timeout=widget_instance.cache_timeout,
            detail=f"widget_id={widget_instance.id}",
        )

    items = _decorate_widget_items(
        widget_instance,
        _build_widget_items(widget_instance, language_code, category=category),
        zone_slug,
    )

    if widget_instance.cache_timeout > 0:
        cache.set(cache_key, items, widget_instance.cache_timeout)
        log_cache_event(
            cache_logger,
            component="widget_items",
            action="set",
            cache_key=cache_key,
            language_code=language_code,
            timeout=widget_instance.cache_timeout,
            detail=f"widget_id={widget_instance.id} items={len(items)}",
        )

    return items


def get_processed_widgets_for_zone(zone_slug, language_code=None, *, category=None):
    language_code = language_code or settings.LANGUAGE_CODE

    try:
        zone = WidgetZone.objects.prefetch_related("widgets").get(slug=zone_slug)
    except WidgetZone.DoesNotExist:
        logger.warning("Widget zone with slug '%s' not found.", zone_slug)
        return []

    processed_widgets = []
    for widget_instance in zone.widgets.all():
        image_format = get_widget_image_format(widget_instance, zone_slug)
        items = get_widget_items(
            widget_instance,
            language_code,
            zone_slug,
            category=category,
        )
        if (
            widget_instance.widget_type == Widget.WidgetType.CATEGORY_TAG_CLOUD
            and not items
        ):
            continue
        processed_widgets.append(
            {
                "widget": widget_instance,
                "items": items,
                "image_format": image_format,
                "prefer_square_image": image_format == Widget.ImageFormat.SQUARE,
            }
        )

    return processed_widgets
