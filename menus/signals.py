# File: menus/signals.py
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import MenuItem, Menu
from .cache_keys import (
    menu_cache_keys_for_slug,
)

SOCIAL_MENU_SLUG = 'social-links'


def clear_cache_for_menu_slug(menu_slug):
    if not menu_slug:
        return

    for cache_key in menu_cache_keys_for_slug(menu_slug):
        cache.delete(cache_key)


def clear_all_menu_caches():
    for menu_slug in Menu.objects.values_list('slug', flat=True):
        clear_cache_for_menu_slug(menu_slug)


def clear_cache_for_menu_slugs(*menu_slugs):
    for menu_slug in {slug for slug in menu_slugs if slug}:
        clear_cache_for_menu_slug(menu_slug)


@receiver(pre_save, sender=MenuItem)
def remember_previous_menu_for_menu_item(sender, instance, **kwargs):
    instance._previous_menu_slug = None
    if not instance.pk:
        return

    instance._previous_menu_slug = (
        MenuItem.objects.filter(pk=instance.pk)
        .values_list("menu__slug", flat=True)
        .first()
    )


@receiver([post_save, post_delete], sender=MenuItem)
def clear_menu_item_cache(sender, instance, **kwargs):
    clear_cache_for_menu_slugs(
        getattr(instance, "_previous_menu_slug", None),
        getattr(instance.menu, "slug", None),
    )


@receiver(pre_save, sender=Menu)
def remember_previous_slug_for_menu(sender, instance, **kwargs):
    instance._previous_slug = None
    if not instance.pk:
        return

    instance._previous_slug = (
        Menu.objects.filter(pk=instance.pk)
        .values_list("slug", flat=True)
        .first()
    )


@receiver([post_save, post_delete], sender=Menu)
def clear_menu_container_cache(sender, instance, **kwargs):
    clear_cache_for_menu_slugs(
        getattr(instance, "_previous_slug", None),
        instance.slug,
    )
