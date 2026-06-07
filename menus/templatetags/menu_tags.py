# File: menus/templatetags/menu_tags.py
from django import template
from django.conf import settings

from menus.selectors import (
    attach_visible_children_for_user,
    filter_visible_menu_items,
    get_main_menu_nodes,
    get_simple_menu_items,
    get_social_menu_items,
)


register = template.Library()


def _get_context_user(context):
    request = context.get("request")
    return getattr(request, "user", None)


@register.inclusion_tag("menus/partials/_navbar_main_level.html", takes_context=True)
def show_menu(context, menu_slug):
    language_code = context.get("LANGUAGE_CODE", settings.LANGUAGE_CODE)
    user = _get_context_user(context)
    top_level_nodes = get_main_menu_nodes(menu_slug, language_code)
    visible_top_level_nodes = filter_visible_menu_items(top_level_nodes, user)
    visible_top_level_nodes = attach_visible_children_for_user(
        visible_top_level_nodes,
        user,
    )
    return {
        "nodes": visible_top_level_nodes,
        "user": user,
    }


@register.inclusion_tag("menus/partials/_social_links_partial.html", takes_context=True)
def show_social_links_menu(context):
    language_code = context.get("LANGUAGE_CODE", settings.LANGUAGE_CODE)
    user = _get_context_user(context)
    menu_items = get_social_menu_items(language_code)
    visible_items = filter_visible_menu_items(menu_items, user)
    return {
        "nodes": visible_items,
        "user": user,
    }


@register.inclusion_tag("menus/partials/_simple_horizontal_menu.html", takes_context=True)
def show_simple_menu(context, menu_slug):
    language_code = context.get("LANGUAGE_CODE", settings.LANGUAGE_CODE)
    user = _get_context_user(context)
    items = get_simple_menu_items(menu_slug, language_code)
    visible_items = filter_visible_menu_items(items, user)
    return {
        "nodes": visible_items,
        "user": user,
    }


@register.inclusion_tag("menus/partials/_profile_links_partial.html", takes_context=True)
def show_profile_menu(context, menu_slug="profile-menu"):
    language_code = context.get("LANGUAGE_CODE", settings.LANGUAGE_CODE)
    user = _get_context_user(context)
    items = get_simple_menu_items(menu_slug, language_code)
    visible_items = filter_visible_menu_items(items, user)
    for item in visible_items:
        item.resolved_url = item.get_url_for_user(user)
    return {
        "nodes": visible_items,
        "user": user,
    }
