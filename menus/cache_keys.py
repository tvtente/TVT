from django.conf import settings


MENU_CACHE_VERSION = "v1"


def main_menu_cache_key(menu_slug, language_code):
    return f"menu_nodes_main_level_{menu_slug}_{language_code}_{MENU_CACHE_VERSION}"


def simple_menu_cache_key(menu_slug, language_code):
    return f"simple_menu_items_{menu_slug}_{language_code}_{MENU_CACHE_VERSION}"


def social_menu_cache_key(language_code):
    return f"social_links_menu_{language_code}_{MENU_CACHE_VERSION}"


def menu_cache_keys_for_slug(menu_slug, languages=None):
    languages = languages or settings.LANGUAGES
    keys = []
    for lang_code, _ in languages:
        keys.append(main_menu_cache_key(menu_slug, lang_code))
        keys.append(simple_menu_cache_key(menu_slug, lang_code))
        if menu_slug == "social-links":
            keys.append(social_menu_cache_key(lang_code))
    return keys
