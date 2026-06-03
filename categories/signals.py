# File: categories/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from menus.models import MenuItem
from menus.signals import clear_all_menu_caches

from .models import Category
from .cache_keys import category_tree_cache_keys

CategoryTranslation = Category._parler_meta.root_model


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=CategoryTranslation)
def clear_category_tree_cache(sender, instance, **kwargs):
    """
    Clears the cached category tree for all languages whenever a category
    is saved or deleted.
    """
    for cache_key in category_tree_cache_keys():
        cache.delete(cache_key)

    clear_all_menu_caches()

    if sender is Category and kwargs.get("signal") is post_delete:
        MenuItem.objects.filter(
            link_type=MenuItem.LinkType.CATEGORY,
            link_category__isnull=True,
        ).delete()
