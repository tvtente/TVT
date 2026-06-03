from django.conf import settings


CATEGORY_TREE_CACHE_VERSION = "v1"


def category_tree_cache_key(language_code):
    return f"full_category_tree_nodes_{language_code}_{CATEGORY_TREE_CACHE_VERSION}"


def category_tree_cache_keys(languages=None):
    languages = languages or settings.LANGUAGES
    return [
        category_tree_cache_key(lang_code)
        for lang_code, _ in languages
    ]
