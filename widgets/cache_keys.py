from django.conf import settings


WIDGET_CACHE_VERSION = "v3"


def widget_items_cache_key(widget_id, language_code, zone_slug):
    return f"widget_items_{widget_id}_{language_code}_{zone_slug}_{WIDGET_CACHE_VERSION}"


def widget_cache_keys_for_widget(widget_id, zone_slug, languages=None):
    languages = languages or settings.LANGUAGES
    return [
        widget_items_cache_key(widget_id, lang_code, zone_slug)
        for lang_code, _ in languages
    ]
