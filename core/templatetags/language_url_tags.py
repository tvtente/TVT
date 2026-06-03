from django import template

from core.language_urls import get_best_language_url


register = template.Library()


@register.simple_tag(takes_context=True)
def language_url(context, target_language):
    request = context.get("request")
    current_path = request.get_full_path() if request else "/"
    return get_best_language_url(
        current_path,
        target_language,
        translatable_object=context.get("translatable_object"),
        language_urls=context.get("language_urls"),
    )
