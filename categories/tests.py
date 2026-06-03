from django.core.cache import cache
from django.test import TestCase, override_settings

from categories.cache_keys import category_tree_cache_key, category_tree_cache_keys
from categories.signals import clear_category_tree_cache


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class CategoryCacheTests(TestCase):
    def test_category_tree_cache_keys_return_all_language_keys(self):
        keys = category_tree_cache_keys()

        self.assertEqual(
            keys,
            [
                category_tree_cache_key("en"),
                category_tree_cache_key("es"),
            ],
        )

    def test_clear_category_tree_cache_deletes_all_language_keys(self):
        key_en = category_tree_cache_key("en")
        key_es = category_tree_cache_key("es")
        cache.set(key_en, ["en"], 300)
        cache.set(key_es, ["es"], 300)

        clear_category_tree_cache(sender=None, instance=None)

        self.assertIsNone(cache.get(key_en))
        self.assertIsNone(cache.get(key_es))
