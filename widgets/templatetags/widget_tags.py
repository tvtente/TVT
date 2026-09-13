# File: widgets/templatetags/widget_tags.py
from django import template
from django.conf import settings

from widgets.selectors import get_processed_widgets_for_zone


register = template.Library()


@register.inclusion_tag("widgets/render_zone.html", takes_context=True)
def show_widget_zone(context, zone_slug, category=None):
    """
    Thin template adapter for widget zones.

    Data retrieval, caching and widget-specific query logic live in
    widgets.selectors so the template layer stays easier to test and debug.
    """
    language_code = context.get("LANGUAGE_CODE", settings.LANGUAGE_CODE)
    if category is None:
        processed_widgets = get_processed_widgets_for_zone(zone_slug, language_code)
    else:
        processed_widgets = get_processed_widgets_for_zone(
            zone_slug,
            language_code,
            category=category,
        )
    return {
        "processed_widgets": processed_widgets,
        "request": context["request"],
        "zone_slug": zone_slug,
    }
