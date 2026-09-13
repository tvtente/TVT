import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils.translation import get_language

from categories.models import Category
from core.cache_observability import get_cache_logger, log_cache_event
from menus.cache_keys import (
    main_menu_cache_key,
    simple_menu_cache_key,
    social_menu_cache_key,
)
from menus.models import Menu, MenuItem
from pages.models import Page
from posts.selectors import get_posts_for_list_type

try:
    from site_settings.models import SiteConfiguration
except ImportError:  # pragma: no cover - defensive only
    SiteConfiguration = None


logger = logging.getLogger(__name__)
cache_logger = get_cache_logger("menus")

SOCIAL_MENU_SLUG = "social-links"


def get_menu_timeout(default=3600):
    if SiteConfiguration is None:
        return default
    try:
        return SiteConfiguration.get_solo().menu_cache_timeout
    except SiteConfiguration.DoesNotExist:
        return default


def filter_visible_menu_items(items, user):
    return [item for item in items if item.is_visible_for_user(user)]


def attach_visible_children_for_user(nodes, user):
    for node in nodes:
        children = list(
            node.get_children()
            .prefetch_related("allowed_groups")
            .order_by("tree_id", "lft")
        )
        visible_children = filter_visible_menu_items(children, user)
        attach_visible_children_for_user(visible_children, user)
        node.visible_children = visible_children
    return nodes


def dedupe_menu_items(items):
    seen = set()
    unique_items = []

    for item in items:
        key = (
            (item.get_url() or "").strip().lower(),
            (item.icon_class or "").strip().lower(),
            (item.translated_title or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    return unique_items


def get_dynamic_posts_for_menu_item(item_obj):
    limit = item_obj.dynamic_items_limit or 5
    if not item_obj.post_list_type:
        return []
    return list(get_posts_for_list_type(item_obj.post_list_type)[:limit])


def _get_category_menu_tree(root_category):
    """Build a small presentation tree below a category configured as menu root."""
    categories = list(
        root_category.get_descendants().filter(is_visible=True).order_by("tree_id", "lft")
    )
    categories_by_id = {category.pk: category for category in categories}

    for category in categories:
        category.menu_url = category.get_posts_url()
        category.menu_children = []

    roots = []
    for category in categories:
        parent = categories_by_id.get(category.parent_id)
        if parent is not None:
            parent.menu_children.append(category)
        elif category.parent_id == root_category.pk:
            roots.append(category)

    return roots


def get_blog_category_queryset(item_obj, language_code=None):
    language_code = language_code or get_language()
    categories = Category.objects.language(language_code).filter(
        translations__language_code=language_code,
        is_visible=True,
    )
    if item_obj.link_category:
        # A bound category acts as the editorial root.  Return its descendants
        # as a presentation tree so the navigation can reveal each level on
        # demand instead of flattening the whole taxonomy.
        return _get_category_menu_tree(item_obj.link_category)
    categories = list(
        categories.annotate(
            own_published_posts=Count(
                "posts_posts",
                filter=Q(posts_posts__status="published"),
                distinct=True,
            )
        )
        .order_by("tree_id", "lft")
        .distinct()
    )

    visible_categories = []
    stack = []

    for category in categories:
        while stack and stack[-1]["rght"] < category.lft:
            finished = stack.pop()
            finished["visible"] = finished["visible"] or finished["has_visible_descendant"]
            if finished["visible"]:
                visible_categories.append(finished["category"])
                if stack:
                    stack[-1]["has_visible_descendant"] = True

        stack.append(
            {
                "category": category,
                "rght": category.rght,
                "visible": bool(category.own_published_posts),
                "has_visible_descendant": False,
            }
        )

    while stack:
        finished = stack.pop()
        finished["visible"] = finished["visible"] or finished["has_visible_descendant"]
        if finished["visible"]:
            visible_categories.append(finished["category"])
            if stack:
                stack[-1]["has_visible_descendant"] = True

    visible_categories.sort(key=lambda category: (category.tree_id, category.lft))

    for category in visible_categories:
        category.menu_url = category.get_posts_url()

    return visible_categories


def _attach_dynamic_children(all_menu_items):
    default_blog_cat_limit = (
        getattr(SiteConfiguration.get_solo(), "blog_items_per_page", 9)
        if SiteConfiguration
        else 9
    )
    default_important_pages_limit = (
        getattr(SiteConfiguration.get_solo(), "search_importance_limit", 3)
        if SiteConfiguration
        else 3
    )

    for item_obj in all_menu_items:
        item_obj.dynamic_children = []
        item_limit = item_obj.dynamic_items_limit or default_blog_cat_limit

        if item_obj.link_type == MenuItem.LinkType.ALL_BLOG_CATEGORIES:
            blog_categories = get_blog_category_queryset(item_obj, get_language())
            item_obj.dynamic_children = list(blog_categories[:item_limit])

        elif item_obj.link_type == MenuItem.LinkType.IMPORTANT_PAGES:
            important_pages_qs = Page.objects.filter(
                status="published",
                importance_order__lt=99,
            ).order_by("importance_order", "title")
            item_obj.dynamic_children = list(
                important_pages_qs[
                    : item_obj.dynamic_items_limit or default_important_pages_limit
                ]
            )

        elif item_obj.link_type == MenuItem.LinkType.POST_LIST:
            item_obj.dynamic_children = get_dynamic_posts_for_menu_item(item_obj)

    return all_menu_items


def get_main_menu_nodes(menu_slug, language_code):
    cache_key = main_menu_cache_key(menu_slug, language_code)
    top_level_nodes = cache.get(cache_key)

    if top_level_nodes is None:
        log_cache_event(
            cache_logger,
            component="main_menu",
            action="miss",
            cache_key=cache_key,
            language_code=language_code,
            detail=f"menu_slug={menu_slug}",
        )
        try:
            menu = Menu.objects.language(language_code).get(slug=menu_slug)
            all_menu_items = list(
                menu.items.all().prefetch_related("allowed_groups").order_by("tree_id", "lft")
            )
            _attach_dynamic_children(all_menu_items)
            top_level_nodes = [item for item in all_menu_items if item.level == 0]

            timeout = get_menu_timeout()
            if timeout > 0:
                cache.set(cache_key, top_level_nodes, timeout)
                log_cache_event(
                    cache_logger,
                    component="main_menu",
                    action="set",
                    cache_key=cache_key,
                    language_code=language_code,
                    timeout=timeout,
                    detail=f"menu_slug={menu_slug} nodes={len(top_level_nodes)}",
                )
        except Menu.DoesNotExist:
            logger.warning("Menu with slug '%s' does not exist.", menu_slug)
            top_level_nodes = []
    else:
        log_cache_event(
            cache_logger,
            component="main_menu",
            action="hit",
            cache_key=cache_key,
            language_code=language_code,
            detail=f"menu_slug={menu_slug}",
        )

    return top_level_nodes


def get_social_menu_items(language_code):
    cache_key = social_menu_cache_key(language_code)
    menu_items_processed = cache.get(cache_key)

    if menu_items_processed is None:
        log_cache_event(
            cache_logger,
            component="social_menu",
            action="miss",
            cache_key=cache_key,
            language_code=language_code,
            detail=f"menu_slug={SOCIAL_MENU_SLUG}",
        )
        timeout = get_menu_timeout()
        menu = (
            Menu.objects.language(language_code)
            .filter(slug=SOCIAL_MENU_SLUG)
            .annotate(item_count=Count("items"))
            .filter(item_count__gt=0)
            .first()
        )
        if menu:
            menu_items_processed = dedupe_menu_items(
                list(
                    menu.items.filter(level=0)
                    .prefetch_related("allowed_groups")
                    .order_by("order", "id")
                )
            )
            if timeout > 0:
                cache.set(cache_key, menu_items_processed, timeout)
                log_cache_event(
                    cache_logger,
                    component="social_menu",
                    action="set",
                    cache_key=cache_key,
                    language_code=language_code,
                    timeout=timeout,
                    detail=f"items={len(menu_items_processed)}",
                )
        else:
            logger.warning("No social menu found. Expected slug: %s", SOCIAL_MENU_SLUG)
            menu_items_processed = []
    else:
        log_cache_event(
            cache_logger,
            component="social_menu",
            action="hit",
            cache_key=cache_key,
            language_code=language_code,
        )

    return menu_items_processed


def get_simple_menu_items(menu_slug, language_code):
    cache_key = simple_menu_cache_key(menu_slug, language_code)
    items = cache.get(cache_key)

    if items is None:
        log_cache_event(
            cache_logger,
            component="simple_menu",
            action="miss",
            cache_key=cache_key,
            language_code=language_code,
            detail=f"menu_slug={menu_slug}",
        )
        try:
            menu = Menu.objects.language(language_code).get(slug=menu_slug)
            items = list(
                menu.items.filter(level=0)
                .prefetch_related("allowed_groups")
                .order_by("order")
            )
            timeout = get_menu_timeout()
            if timeout > 0:
                cache.set(cache_key, items, timeout)
                log_cache_event(
                    cache_logger,
                    component="simple_menu",
                    action="set",
                    cache_key=cache_key,
                    language_code=language_code,
                    timeout=timeout,
                    detail=f"menu_slug={menu_slug} items={len(items)}",
                )
        except Menu.DoesNotExist:
            logger.warning(
                "Menu with slug '%s' does not exist for show_simple_menu.",
                menu_slug,
            )
            items = []
    else:
        log_cache_event(
            cache_logger,
            component="simple_menu",
            action="hit",
            cache_key=cache_key,
            language_code=language_code,
            detail=f"menu_slug={menu_slug}",
        )

    return items
