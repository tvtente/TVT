import tempfile
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from books.models import Book
from publications.models import Publication
from widgets.cache_keys import widget_items_cache_key
from widgets.models import Widget, WidgetZone
from widgets.selectors import get_processed_widgets_for_zone, get_widget_items
from widgets.signals import clear_all_widget_caches
from widgets.templatetags.widget_tags import show_widget_zone
from categories.models import Category
from gallery.models import Image
from posts.models import Post, PostFavorite, PostPointAllocation


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class WidgetCacheInvalidationTests(TestCase):
    def setUp(self):
        self.zone = WidgetZone.objects.create(name="Sidebar", slug="sidebar-right")

    def test_clear_all_widget_caches_deletes_render_cache_keys(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=300,
        )

        key_en = widget_items_cache_key(widget.id, "en", self.zone.slug)
        key_es = widget_items_cache_key(widget.id, "es", self.zone.slug)
        cache.set(key_en, ["cached-en"], 300)
        cache.set(key_es, ["cached-es"], 300)

        clear_all_widget_caches()

        self.assertIsNone(cache.get(key_en))
        self.assertIsNone(cache.get(key_es))

    def test_widget_save_invalidates_only_that_widget_cache(self):
        changed_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=300,
        )
        untouched_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        changed_key = widget_items_cache_key(changed_widget.id, "en", self.zone.slug)
        untouched_key = widget_items_cache_key(untouched_widget.id, "en", self.zone.slug)
        cache.set(changed_key, ["changed"], 300)
        cache.set(untouched_key, ["untouched"], 300)

        changed_widget.title = "Recent updated"
        changed_widget.save()

        self.assertIsNone(cache.get(changed_key))
        self.assertEqual(cache.get(untouched_key), ["untouched"])

    def test_widget_zone_change_invalidates_old_and_new_zone_keys(self):
        other_zone = WidgetZone.objects.create(name="Homepage", slug="homepage-content-grid")
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=300,
        )
        old_key = widget_items_cache_key(widget.id, "en", self.zone.slug)
        new_key = widget_items_cache_key(widget.id, "en", other_zone.slug)
        cache.set(old_key, ["old-zone"], 300)
        cache.set(new_key, ["new-zone"], 300)

        widget.zone = other_zone
        widget.save()

        self.assertIsNone(cache.get(old_key))
        self.assertIsNone(cache.get(new_key))

    def test_post_change_invalidates_post_widgets_but_not_unrelated_widgets(self):
        post_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=300,
        )
        unrelated_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        post_key = widget_items_cache_key(post_widget.id, "en", self.zone.slug)
        unrelated_key = widget_items_cache_key(unrelated_widget.id, "en", self.zone.slug)
        cache.set(post_key, ["post"], 300)
        cache.set(unrelated_key, ["users"], 300)

        author = get_user_model().objects.create_user(username="post-author", password="p")
        post = Post.objects.create(author=author, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Fresh post"
        post.slug = "fresh-post"
        post.content = "content"
        post.save()

        self.assertIsNone(cache.get(post_key))
        self.assertEqual(cache.get(unrelated_key), ["users"])

    def test_post_point_allocation_change_invalidates_widget_cache(self):
        points_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_TOP_RATED_TODAY,
            title="Top rated today",
            cache_timeout=300,
        )
        unrelated_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        points_key = widget_items_cache_key(points_widget.id, "en", self.zone.slug)
        unrelated_key = widget_items_cache_key(unrelated_widget.id, "en", self.zone.slug)
        cache.set(points_key, ["cached-en"], 300)
        cache.set(unrelated_key, ["users"], 300)

        author = get_user_model().objects.create_user(username="alloc-author", password="p")
        voter = get_user_model().objects.create_user(username="alloc-voter", password="p")
        post = Post.objects.create(author=author, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Allocated post"
        post.slug = "allocated-post"
        post.content = "content"
        post.save()

        PostPointAllocation.objects.create(
            user=voter,
            post=post,
            points=3,
            date=timezone.localdate(),
        )

        self.assertIsNone(cache.get(points_key))
        self.assertEqual(cache.get(unrelated_key), ["users"])

    def test_post_favorite_change_invalidates_favorite_widgets_only(self):
        favorite_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_MOST_FAVORITED,
            title="Most favorited",
            cache_timeout=300,
        )
        unrelated_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        favorite_key = widget_items_cache_key(favorite_widget.id, "en", self.zone.slug)
        unrelated_key = widget_items_cache_key(unrelated_widget.id, "en", self.zone.slug)
        cache.set(favorite_key, ["favorites"], 300)
        cache.set(unrelated_key, ["users"], 300)

        author = get_user_model().objects.create_user(username="favorite-author", password="p")
        user = get_user_model().objects.create_user(username="favorite-user", password="p")
        post = Post.objects.create(author=author, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Favorited post"
        post.slug = "favorited-post"
        post.content = "content"
        post.save()

        PostFavorite.objects.create(user=user, post=post)

        self.assertIsNone(cache.get(favorite_key))
        self.assertEqual(cache.get(unrelated_key), ["users"])

    def test_book_change_invalidates_book_widgets_only(self):
        book_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.BOOK_GRID_RECENT,
            title="Books",
            cache_timeout=300,
        )
        unrelated_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        book_key = widget_items_cache_key(book_widget.id, "en", self.zone.slug)
        unrelated_key = widget_items_cache_key(unrelated_widget.id, "en", self.zone.slug)
        cache.set(book_key, ["books"], 300)
        cache.set(unrelated_key, ["users"], 300)

        book = Book.objects.create(is_published=True)
        book.set_current_language("en")
        book.title = "Fresh book"
        book.slug = "fresh-book"
        book.description = "description"
        book.save()

        self.assertIsNone(cache.get(book_key))
        self.assertEqual(cache.get(unrelated_key), ["users"])

    def test_publication_change_invalidates_publication_widgets_only(self):
        publication_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.PUBLICATION_GRID_RECENT,
            title="Publications",
            cache_timeout=300,
        )
        unrelated_widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.USER_DIRECTORY,
            title="Users",
            cache_timeout=300,
        )
        publication_key = widget_items_cache_key(publication_widget.id, "en", self.zone.slug)
        unrelated_key = widget_items_cache_key(unrelated_widget.id, "en", self.zone.slug)
        cache.set(publication_key, ["publications"], 300)
        cache.set(unrelated_key, ["users"], 300)

        publication = Publication.objects.create(is_published=True)
        publication.set_current_language("en")
        publication.title = "Fresh publication"
        publication.slug = "fresh-publication"
        publication.abstract = "abstract"
        publication.save()

        self.assertIsNone(cache.get(publication_key))
        self.assertEqual(cache.get(unrelated_key), ["users"])


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish"), ("ca", "Catalan")), MEDIA_ROOT=tempfile.mkdtemp())
class WidgetSelectorTests(TestCase):
    def setUp(self):
        self.zone = WidgetZone.objects.create(name="Sidebar", slug="sidebar-right")
        self.widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.BLOG_CATEGORIES,
            title="Categorias",
            cache_timeout=0,
            item_count=10,
        )
        self.user = get_user_model().objects.create_user(username="author", password="p")

    def _create_post_with_image(self, slug, title):
        featured_image = Image(title=title, slug=f"{slug}-featured", language="en", description="")
        featured_image.image.save(f"{slug}-featured.jpg", ContentFile(b"featured"), save=True)
        social_image = Image(title=title, slug=f"{slug}-social", language="en", description="")
        social_image.image.save(f"{slug}-social.jpg", ContentFile(b"social"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = title
        post.slug = slug
        post.content = "content"
        post.featured_image_asset = featured_image
        post.social_image_asset = social_image
        post.save()
        return post

    def test_blog_category_widget_returns_each_category_once_in_active_language(self):
        category = Category.objects.create()
        category.set_current_language("es")
        category.name = "Salud"
        category.slug = "salud"
        category.save()

        category.set_current_language("en")
        category.name = "Health"
        category.slug = "health"
        category.save()

        category.set_current_language("ca")
        category.name = "Salut"
        category.slug = "salut"
        category.save()

        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("es")
        post.title = "Articulo"
        post.slug = "articulo"
        post.content = "contenido"
        post.save()
        post.categories.add(category)

        items = get_widget_items(self.widget, "es", self.zone.slug)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].pk, category.pk)
        self.assertEqual(items[0].safe_translation_getter("name", language_code="es"), "Salud")
        self.assertEqual(items[0].num_posts, 1)

    def test_recent_posts_widget_leaves_thumbnail_empty_when_post_has_no_images(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=0,
            item_count=10,
        )
        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("en")
        post.title = "No image post"
        post.slug = "no-image-post"
        post.content = "content"
        post.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual(items[0].thumbnail_url, "")

    def test_recent_posts_widget_prefers_mobile_thumbnail_over_social(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent",
            cache_timeout=0,
            item_count=10,
        )
        featured_image = Image(title="Featured", slug="thumb-featured", language="en", description="")
        featured_image.image.save("thumb-featured.jpg", ContentFile(b"featured"), save=True)
        social_image = Image(title="Social", slug="thumb-social", language="en", description="")
        social_image.image.save("thumb-social.jpg", ContentFile(b"social"), save=True)
        mobile_image = Image(title="Mobile", slug="thumb-mobile", language="en", description="")
        mobile_image.image.save("thumb-mobile.jpg", ContentFile(b"mobile"), save=True)

        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("en")
        post.title = "Thumb priority"
        post.slug = "thumb-priority"
        post.content = "content"
        post.featured_image_asset = featured_image
        post.social_image_asset = social_image
        post.mobile_image_asset = mobile_image
        post.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertTrue(items[0].thumbnail_url.endswith("thumb-mobile.jpg"))
        self.assertEqual(items[0].thumbnail_kind, "mobile")

    def test_top_rated_today_widget_orders_posts_by_today_points(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_TOP_RATED_TODAY,
            title="Top rated today",
            cache_timeout=0,
            item_count=10,
        )
        top_post = self._create_post_with_image("top-today", "Top today")
        second_post = self._create_post_with_image("second-today", "Second today")

        PostPointAllocation.objects.create(user=self.user, post=top_post, points=5, date=timezone.localdate())
        other_user = get_user_model().objects.create_user(username="reader2", password="p")
        PostPointAllocation.objects.create(user=other_user, post=second_post, points=3, date=timezone.localdate())

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [top_post.pk, second_post.pk])
        self.assertEqual(items[0].total_points, 5)
        self.assertEqual(items[1].total_points, 3)

    def test_top_rated_week_widget_includes_previous_days_within_window(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_TOP_RATED_WEEK,
            title="Top rated week",
            cache_timeout=0,
            item_count=10,
        )
        week_post = self._create_post_with_image("week-post", "Week post")
        today_post = self._create_post_with_image("today-post", "Today post")

        PostPointAllocation.objects.create(
            user=self.user,
            post=week_post,
            points=4,
            date=timezone.localdate() - timezone.timedelta(days=3),
        )
        other_user = get_user_model().objects.create_user(username="reader3", password="p")
        PostPointAllocation.objects.create(
            user=other_user,
            post=today_post,
            points=2,
            date=timezone.localdate(),
        )

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [week_post.pk, today_post.pk])
        self.assertEqual(items[0].total_points, 4)
        self.assertEqual(items[1].total_points, 2)

    def test_most_favorited_widget_orders_posts_by_favorite_count(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_MOST_FAVORITED,
            title="Most favorited",
            cache_timeout=0,
            item_count=10,
        )
        top_post = self._create_post_with_image("favorite-top", "Favorite top")
        second_post = self._create_post_with_image("favorite-second", "Favorite second")

        second_user = get_user_model().objects.create_user(username="favorite-reader-2", password="p")
        third_user = get_user_model().objects.create_user(username="favorite-reader-3", password="p")

        PostFavorite.objects.create(user=self.user, post=top_post)
        PostFavorite.objects.create(user=second_user, post=top_post)
        PostFavorite.objects.create(user=third_user, post=second_post)

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [top_post.pk, second_post.pk])
        self.assertEqual(items[0].total_favorites, 2)
        self.assertEqual(items[1].total_favorites, 1)

    def test_community_picks_widget_uses_combined_score(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_COMMUNITY_PICKS,
            title="Community picks",
            cache_timeout=0,
            item_count=10,
        )
        points_post = self._create_post_with_image("community-points", "Community points")
        editorial_post = self._create_post_with_image("community-editorial", "Community editorial")
        editorial_post.editor_rating = 90
        editorial_post.save(update_fields=["editor_rating"])

        PostPointAllocation.objects.create(
            user=self.user,
            post=points_post,
            points=4,
            date=timezone.localdate(),
        )
        other_user = get_user_model().objects.create_user(username="reader4", password="p")
        PostPointAllocation.objects.create(
            user=other_user,
            post=editorial_post,
            points=2,
            date=timezone.localdate(),
        )

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [points_post.pk, editorial_post.pk])
        self.assertEqual(items[0].community_score, 400)
        self.assertEqual(items[1].community_score, 290)

    def test_processed_widgets_for_zone_adds_sidebar_render_flag(self):
        processed = get_processed_widgets_for_zone(self.zone.slug, "es")

        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]["widget"].pk, self.widget.pk)
        self.assertEqual(processed[0]["items"], [])
        self.assertTrue(processed[0]["prefer_square_image"])

    def test_auto_image_format_uses_social_image_for_sidebar_zone(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_RECENT,
            title="Sidebar posts",
            cache_timeout=0,
            item_count=10,
        )
        post = self._create_post_with_image("sidebar-post", "Sidebar post")

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual(items[0].widget_image_format, Widget.ImageFormat.SQUARE)
        self.assertEqual(items[0].widget_display_image.name, post.get_social_image().name)

    def test_explicit_landscape_image_format_prefers_featured_image(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_RECENT,
            title="Landscape posts",
            cache_timeout=0,
            item_count=10,
            image_format=Widget.ImageFormat.LANDSCAPE,
        )
        post = self._create_post_with_image("landscape-post", "Landscape post")

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual(items[0].widget_image_format, Widget.ImageFormat.LANDSCAPE)
        self.assertEqual(items[0].widget_display_image.name, post.get_featured_image().name)

    def test_explicit_mobile_image_format_prefers_mobile_image(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_RECENT,
            title="Mobile posts",
            cache_timeout=0,
            item_count=10,
            image_format=Widget.ImageFormat.MOBILE,
        )
        featured_image = Image(title="Featured", slug="mobile-format-featured", language="en", description="")
        featured_image.image.save("mobile-format-featured.jpg", ContentFile(b"featured"), save=True)
        social_image = Image(title="Social", slug="mobile-format-social", language="en", description="")
        social_image.image.save("mobile-format-social.jpg", ContentFile(b"social"), save=True)
        mobile_image = Image(title="Mobile", slug="mobile-format-mobile", language="en", description="")
        mobile_image.image.save("mobile-format-mobile.jpg", ContentFile(b"mobile"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Mobile post"
        post.slug = "mobile-post"
        post.content = "content"
        post.featured_image_asset = featured_image
        post.social_image_asset = social_image
        post.mobile_image_asset = mobile_image
        post.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual(items[0].widget_image_format, Widget.ImageFormat.MOBILE)
        self.assertEqual(items[0].widget_display_image.name, post.get_mobile_image().name)

    def test_hero_carousel_returns_featured_posts_by_editor_rating(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.HERO_CAROUSEL,
            title="Hero",
            cache_timeout=0,
            item_count=10,
        )
        high_post = self._create_post_with_image("hero-high", "Hero high")
        high_post.editor_rating = 95
        high_post.save(update_fields=["editor_rating"])
        low_post = self._create_post_with_image("hero-low", "Hero low")
        low_post.editor_rating = 70
        low_post.save(update_fields=["editor_rating"])

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [high_post.pk, low_post.pk])

    def test_hero_carousel_includes_posts_without_image(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.HERO_CAROUSEL,
            title="Hero",
            cache_timeout=0,
            item_count=10,
        )
        imaged_post = self._create_post_with_image("hero-image", "Hero image")
        imaged_post.editor_rating = 80
        imaged_post.save(update_fields=["editor_rating"])

        no_image_post = Post.objects.create(
            author=self.user,
            status="published",
            show_in_post_grids=True,
            editor_rating=90,
        )
        no_image_post.set_current_language("en")
        no_image_post.title = "Hero no image"
        no_image_post.slug = "hero-no-image"
        no_image_post.content = "content"
        no_image_post.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [no_image_post.pk, imaged_post.pk])
        self.assertIsNone(items[0].widget_display_image)

    def test_book_grid_recent_returns_only_published_books_in_language_order(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.BOOK_GRID_RECENT,
            title="Books",
            cache_timeout=0,
            item_count=10,
        )
        visible = Book.objects.create(is_published=True)
        visible.set_current_language("en")
        visible.title = "Visible book"
        visible.slug = "visible-book"
        visible.description = "description"
        visible.save()

        hidden = Book.objects.create(is_published=False)
        hidden.set_current_language("en")
        hidden.title = "Hidden book"
        hidden.slug = "hidden-book"
        hidden.description = "description"
        hidden.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [visible.pk])

    def test_publication_grid_recent_returns_only_published_publications(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.PUBLICATION_GRID_RECENT,
            title="Publications",
            cache_timeout=0,
            item_count=10,
        )
        visible = Publication.objects.create(is_published=True)
        visible.authors.add(self.user)
        visible.set_current_language("en")
        visible.title = "Visible publication"
        visible.slug = "visible-publication"
        visible.abstract = "abstract"
        visible.save()

        hidden = Publication.objects.create(is_published=False)
        hidden.authors.add(self.user)
        hidden.set_current_language("en")
        hidden.title = "Hidden publication"
        hidden.slug = "hidden-publication"
        hidden.abstract = "abstract"
        hidden.save()

        items = get_widget_items(widget, "en", self.zone.slug)

        self.assertEqual([item.pk for item in items], [visible.pk])


class WidgetTemplateTagTests(TestCase):
    def test_show_widget_zone_delegates_to_selector_and_returns_request(self):
        request = RequestFactory().get("/")
        fake_processed_widgets = [
            {
                "widget": object(),
                "items": ["a", "b"],
                "prefer_square_image": True,
            }
        ]

        with patch(
            "widgets.templatetags.widget_tags.get_processed_widgets_for_zone",
            return_value=fake_processed_widgets,
        ) as mocked_selector:
            context = {"request": request, "LANGUAGE_CODE": "es"}
            result = show_widget_zone(context, "sidebar-right")

        mocked_selector.assert_called_once_with("sidebar-right", "es")
        self.assertEqual(result["processed_widgets"], fake_processed_widgets)
        self.assertIs(result["request"], request)


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")), MEDIA_ROOT=tempfile.mkdtemp())
class WidgetRenderingTests(TestCase):
    def setUp(self):
        self.zone = WidgetZone.objects.create(name="Homepage", slug="homepage-main-content")
        self.widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.HERO_CAROUSEL,
            title="Homepage hero",
            section_title="Featured",
            cache_timeout=0,
            item_count=3,
        )
        self.user = get_user_model().objects.create_user(username="hero-author", password="p")

    def _render_widget(self, widget, items):
        return render_to_string(
            "widgets/render_zone.html",
            {
                "processed_widgets": [
                    {
                        "widget": widget,
                        "items": items,
                        "image_format": widget.image_format,
                        "prefer_square_image": False,
                    }
                ],
                "request": RequestFactory().get("/"),
            },
        )

    def test_hero_carousel_template_renders(self):
        image = Image(title="Hero", slug="hero-render-image", language="en", description="")
        image.image.save("hero-render.jpg", ContentFile(b"img"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Hero article"
        post.slug = "hero-article"
        post.summary = "Summary"
        post.content = "content"
        post.featured_image_asset = image
        post.save()
        post.widget_display_image = image.image
        post.widget_image_format = Widget.ImageFormat.LANDSCAPE

        html = self._render_widget(self.widget, [post])

        self.assertIn("hero-carousel", html)
        self.assertIn("Hero article", html)
        self.assertIn("zoomable", html)
        self.assertIn("hero-carousel__caption-box", html)

    def test_hero_carousel_template_respects_square_image_format(self):
        self.widget.image_format = Widget.ImageFormat.SQUARE
        self.widget.save(update_fields=["image_format"])

        image = Image(title="Hero square", slug="hero-square-image", language="en", description="")
        image.image.save("hero-square.jpg", ContentFile(b"img"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Hero square article"
        post.slug = "hero-square-article"
        post.content = "content"
        post.social_image_asset = image
        post.save()
        post.widget_display_image = post.get_social_image()
        post.widget_image_format = Widget.ImageFormat.SQUARE

        html = self._render_widget(self.widget, [post])

        self.assertIn("aspect-ratio: 1 / 1", html)

    def test_hero_carousel_template_respects_mobile_image_format(self):
        self.widget.image_format = Widget.ImageFormat.MOBILE
        self.widget.save(update_fields=["image_format"])

        image = Image(title="Hero mobile", slug="hero-mobile-image", language="en", description="")
        image.image.save("hero-mobile.jpg", ContentFile(b"img"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Hero mobile article"
        post.slug = "hero-mobile-article"
        post.content = "content"
        post.mobile_image_asset = image
        post.save()
        post.widget_display_image = post.get_mobile_image()
        post.widget_image_format = Widget.ImageFormat.MOBILE

        html = self._render_widget(self.widget, [post])

        self.assertIn("aspect-ratio: 9 / 16", html)

    def test_post_grid_template_uses_square_format_when_requested(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_RECENT,
            title="Posts",
            section_title="Recent posts",
            cache_timeout=0,
            image_format=Widget.ImageFormat.SQUARE,
        )
        featured_image = Image(title="Featured", slug="render-grid-featured", language="en", description="")
        featured_image.image.save("render-grid-featured.jpg", ContentFile(b"featured"), save=True)
        social_image = Image(title="Social", slug="render-grid-social", language="en", description="")
        social_image.image.save("render-grid-social.jpg", ContentFile(b"social"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Rendered post"
        post.slug = "rendered-post"
        post.content = "Body"
        post.featured_image_asset = featured_image
        post.social_image_asset = social_image
        post.save()
        post.widget_display_image = post.get_social_image()
        post.widget_image_format = Widget.ImageFormat.SQUARE

        html = self._render_widget(widget, [post])

        self.assertIn("post-grid-image-square", html)
        self.assertIn("render-grid-social.jpg", html)

    def test_post_grid_template_uses_mobile_format_when_requested(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.POST_GRID_RECENT,
            title="Posts mobile",
            section_title="Recent posts mobile",
            cache_timeout=0,
            image_format=Widget.ImageFormat.MOBILE,
        )
        mobile_image = Image(title="Mobile", slug="render-grid-mobile", language="en", description="")
        mobile_image.image.save("render-grid-mobile.jpg", ContentFile(b"mobile"), save=True)

        post = Post.objects.create(author=self.user, status="published", show_in_post_grids=True)
        post.set_current_language("en")
        post.title = "Rendered mobile post"
        post.slug = "rendered-mobile-post"
        post.content = "Body"
        post.mobile_image_asset = mobile_image
        post.save()
        post.widget_display_image = post.get_mobile_image()
        post.widget_image_format = Widget.ImageFormat.MOBILE

        html = self._render_widget(widget, [post])

        self.assertIn("aspect-ratio: 9 / 16", html)
        self.assertIn("render-grid-mobile.jpg", html)

    def test_book_grid_template_renders(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.BOOK_GRID_RECENT,
            title="Books",
            section_title="Recent books",
            cache_timeout=0,
        )
        book = Book.objects.create(is_published=True)
        book.set_current_language("en")
        book.title = "Rendered book"
        book.slug = "rendered-book"
        book.description = "Description"
        book.save()

        html = self._render_widget(widget, [book])

        self.assertIn("Recent books", html)
        self.assertIn("Rendered book", html)

    def test_publication_grid_template_renders(self):
        widget = Widget.objects.create(
            zone=self.zone,
            widget_type=Widget.WidgetType.PUBLICATION_GRID_RECENT,
            title="Publications",
            section_title="Recent publications",
            cache_timeout=0,
        )
        publication = Publication.objects.create(is_published=True)
        publication.authors.add(self.user)
        publication.set_current_language("en")
        publication.title = "Rendered publication"
        publication.slug = "rendered-publication"
        publication.abstract = "Abstract"
        publication.save()

        html = self._render_widget(widget, [publication])

        self.assertIn("Recent publications", html)
        self.assertIn("Rendered publication", html)
