from django import template

from core.language_urls import get_best_language_url


register = template.Library()


@register.simple_tag(takes_context=True)
def get_translated_url(context, translatable_object=None, language_code=None):
    request = context.get("request")
    current_path = request.get_full_path() if request else "/"
    return get_best_language_url(
        current_path,
        language_code,
        translatable_object=translatable_object,
    )
