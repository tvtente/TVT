from django.core.cache import cache
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from categories.admin import CategoryAdmin
from categories.cache_keys import category_tree_cache_key, category_tree_cache_keys
from categories.signals import clear_category_tree_cache
from categories.models import Category
from menus.cache_keys import main_menu_cache_key
from menus.models import Menu, MenuItem
from posts.models import Post
from django.contrib.auth import get_user_model


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

    def test_category_delete_invalidates_menu_cache(self):
        menu = Menu.objects.create(slug="main-menu")
        category = Category.objects.create(parent=None)
        category.set_current_language("en")
        category.name = "Category"
        category.slug = "category"
        category.save()
        MenuItem.objects.create(
            menu=menu,
            order=1,
            title="Category link",
            link_type=MenuItem.LinkType.CATEGORY,
            link_category=category,
        )
        menu_key = main_menu_cache_key("main-menu", "en")
        cache.set(menu_key, ["cached"], 300)

        category.delete()

        self.assertIsNone(cache.get(menu_key))

    def test_category_delete_removes_orphaned_category_menu_items(self):
        menu = Menu.objects.create(slug="main-menu")
        category = Category.objects.create(parent=None)
        category.set_current_language("en")
        category.name = "Category"
        category.slug = "category"
        category.save()
        menu_item = MenuItem.objects.create(
            menu=menu,
            order=1,
            title="Category link",
            link_type=MenuItem.LinkType.CATEGORY,
            link_category=category,
        )

        category.delete()

        self.assertFalse(MenuItem.objects.filter(pk=menu_item.pk).exists())


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class CategoryAdminDeletionImpactTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = CategoryAdmin(Category, self.site)
        self.user = get_user_model().objects.create_user(username="category-author", password="p")

    def _create_category(self, slug, name):
        category = Category.objects.create(parent=None)
        category.set_current_language("en")
        category.slug = slug
        category.name = name
        category.save()
        return category

    def _create_post(self, slug, title, categories):
        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("en")
        post.slug = slug
        post.title = title
        post.content = "Body"
        post.save()
        post.categories.set(categories)
        return post

    def test_deletion_impact_counts_related_posts_and_uncategorized_posts(self):
        category_a = self._create_category("a", "A")
        category_b = self._create_category("b", "B")
        self._create_post("only-a", "Only A", [category_a])
        self._create_post("a-and-b", "A and B", [category_a, category_b])

        impact = self.admin._get_deletion_impact(Category.objects.filter(pk=category_a.pk))

        self.assertEqual(impact["category_count"], 1)
        self.assertEqual(impact["related_posts_count"], 2)
        self.assertEqual(impact["uncategorized_posts_count"], 1)

    def test_hiding_parent_hides_visible_descendants(self):
        parent = self._create_category("parent", "Parent")
        child = Category.objects.create(parent=parent)
        child.set_current_language("en")
        child.slug = "child"
        child.name = "Child"
        child.save()

        request = RequestFactory().post("/")
        request.session = {}
        request._messages = FallbackStorage(request)
        parent.is_visible = False

        self.admin.save_model(request, parent, form=None, change=True)

        parent.refresh_from_db()
        child.refresh_from_db()
        self.assertFalse(parent.is_visible)
        self.assertFalse(child.is_visible)
