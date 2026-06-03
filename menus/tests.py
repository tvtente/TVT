from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.utils.translation import override

from categories.models import Category
from menus.cache_keys import (
    main_menu_cache_key,
    menu_cache_keys_for_slug,
    simple_menu_cache_key,
    social_menu_cache_key,
)
from menus.models import Menu, MenuItem
from menus.selectors import get_blog_category_queryset, get_main_menu_nodes
from menus.signals import clear_cache_for_menu_slug
from menus.templatetags.menu_tags import show_menu
from posts.models import Post
from django.contrib.auth import get_user_model


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class MenuCacheInvalidationTests(TestCase):
    def setUp(self):
        self.main_menu = Menu.objects.create(slug="main-menu")
        self.footer_menu = Menu.objects.create(slug="footer-menu")

    def test_clear_cache_for_menu_slug_deletes_main_and_simple_menu_keys(self):
        menu_slug = "main-menu"
        key_main_en = main_menu_cache_key(menu_slug, "en")
        key_simple_en = simple_menu_cache_key(menu_slug, "en")
        key_main_es = main_menu_cache_key(menu_slug, "es")
        key_simple_es = simple_menu_cache_key(menu_slug, "es")
        cache.set(key_main_en, ["main-en"], 300)
        cache.set(key_simple_en, ["simple-en"], 300)
        cache.set(key_main_es, ["main-es"], 300)
        cache.set(key_simple_es, ["simple-es"], 300)

        clear_cache_for_menu_slug(menu_slug)

        self.assertIsNone(cache.get(key_main_en))
        self.assertIsNone(cache.get(key_simple_en))
        self.assertIsNone(cache.get(key_main_es))
        self.assertIsNone(cache.get(key_simple_es))

    def test_clear_cache_for_social_menu_slug_deletes_social_keys(self):
        key_en = social_menu_cache_key("en")
        key_es = social_menu_cache_key("es")
        cache.set(key_en, ["social-en"], 300)
        cache.set(key_es, ["social-es"], 300)

        clear_cache_for_menu_slug("social-links")

        self.assertIsNone(cache.get(key_en))
        self.assertIsNone(cache.get(key_es))

    def test_menu_cache_keys_for_slug_returns_all_language_keys(self):
        keys = menu_cache_keys_for_slug("social-links")

        self.assertIn(main_menu_cache_key("social-links", "en"), keys)
        self.assertIn(simple_menu_cache_key("social-links", "en"), keys)
        self.assertIn(social_menu_cache_key("en"), keys)
        self.assertIn(main_menu_cache_key("social-links", "es"), keys)
        self.assertIn(simple_menu_cache_key("social-links", "es"), keys)
        self.assertIn(social_menu_cache_key("es"), keys)

    def test_menu_item_save_invalidates_only_its_menu_slug(self):
        main_key = main_menu_cache_key("main-menu", "en")
        footer_key = main_menu_cache_key("footer-menu", "en")
        cache.set(main_key, ["main"], 300)
        cache.set(footer_key, ["footer"], 300)

        MenuItem.objects.create(
            menu=self.main_menu,
            order=1,
            title="Home",
            link_type=MenuItem.LinkType.HOME,
        )

        self.assertIsNone(cache.get(main_key))
        self.assertEqual(cache.get(footer_key), ["footer"])

    def test_menu_item_move_invalidates_old_and_new_menu_slugs(self):
        main_key = main_menu_cache_key("main-menu", "en")
        footer_key = main_menu_cache_key("footer-menu", "en")
        cache.set(main_key, ["main"], 300)
        cache.set(footer_key, ["footer"], 300)

        item = MenuItem.objects.create(
            menu=self.main_menu,
            order=1,
            title="Home",
            link_type=MenuItem.LinkType.HOME,
        )
        cache.set(main_key, ["main"], 300)
        cache.set(footer_key, ["footer"], 300)

        item.menu = self.footer_menu
        item.save()

        self.assertIsNone(cache.get(main_key))
        self.assertIsNone(cache.get(footer_key))

    def test_menu_slug_change_invalidates_old_and_new_slug_keys(self):
        old_key = main_menu_cache_key("main-menu", "en")
        new_key = main_menu_cache_key("main-menu-renamed", "en")
        cache.set(old_key, ["old"], 300)
        cache.set(new_key, ["new"], 300)

        self.main_menu.slug = "main-menu-renamed"
        self.main_menu.save()

        self.assertIsNone(cache.get(old_key))
        self.assertIsNone(cache.get(new_key))


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class MenuSelectorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="author", password="p")
        self.menu = Menu.objects.create(slug="main-menu")
        self.menu.set_current_language("es")
        self.menu.title = "Principal"
        self.menu.save()

        self.root = MenuItem.objects.create(
            menu=self.menu,
            order=1,
            title="Inicio",
            link_type=MenuItem.LinkType.HOME,
        )
        self.child = MenuItem.objects.create(
            menu=self.menu,
            parent=self.root,
            order=1,
            title="Subitem",
            link_type=MenuItem.LinkType.URL,
            link_url="/sub/",
        )

    def test_get_main_menu_nodes_returns_top_level_nodes(self):
        nodes = get_main_menu_nodes("main-menu", "es")

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].pk, self.root.pk)

    def test_blog_category_queryset_keeps_ancestors_with_published_descendants(self):
        root_category = Category.objects.create(parent=None)
        root_category.set_current_language("es")
        root_category.name = "Padre"
        root_category.slug = "padre"
        root_category.save()

        child_category = Category.objects.create(parent=root_category)
        child_category.set_current_language("es")
        child_category.name = "Hija"
        child_category.slug = "hija"
        child_category.save()

        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("es")
        post.title = "Articulo"
        post.slug = "articulo"
        post.content = "contenido"
        post.save()
        post.categories.add(child_category)

        self.root.link_type = MenuItem.LinkType.ALL_BLOG_CATEGORIES
        self.root.save()

        with override("es"):
            categories = get_blog_category_queryset(self.root)

        self.assertEqual([category.pk for category in categories], [root_category.pk, child_category.pk])
        self.assertTrue(all(hasattr(category, "menu_url") for category in categories))

    def test_show_menu_delegates_to_selector_and_filters_user_visibility(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        fake_root = self.root
        fake_root.visible_children = []

        with patch(
            "menus.templatetags.menu_tags.get_main_menu_nodes",
            return_value=[fake_root],
        ) as mocked_selector:
            result = show_menu({"request": request, "LANGUAGE_CODE": "es"}, "main-menu")

        mocked_selector.assert_called_once_with("main-menu", "es")
        self.assertEqual(len(result["nodes"]), 1)
        self.assertEqual(result["nodes"][0].pk, self.root.pk)
        self.assertIs(result["user"], request.user)

    def test_notebook_list_link_type_resolves_public_notebooks_url(self):
        item = MenuItem.objects.create(
            menu=self.menu,
            order=2,
            title="Cuadernos",
            link_type=MenuItem.LinkType.NOTEBOOK_LIST,
        )

        with override("es"):
            self.assertEqual(item.get_url(), "/es/notebooks/")
