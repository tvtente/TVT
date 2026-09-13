import tempfile
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from gallery.models import Image
from gallery.models import StagedUpload
from accounts.models import UserFollow, UserNotification
from posts.admin import PostAdmin
from posts.models import Post, PostContentBlock, PostFavorite, PostPointAllocation
from posts.selectors import get_posts_for_list_type
from posts.services import get_post_points_summary
from site_settings.models import SiteConfiguration


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PostGalleryAssetDualReadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u1", password="p")

    def test_get_featured_image_prefers_library_asset(self):
        gimg = Image(title="G", slug="g-asset", language="es", description="")
        gimg.image.save("g-asset.jpg", ContentFile(b"1"), save=True)

        post = Post.objects.create(author=self.user)
        post.set_current_language("es")
        post.title = "T"
        post.slug = "t"
        post.content = "c"
        post.featured_image_asset = gimg
        post.save()

        self.assertEqual(post.get_featured_image().name, gimg.image.name)

    def test_get_social_image_prefers_social_asset(self):
        gfeatured = Image(title="F", slug="f-1", language="es", description="")
        gfeatured.image.save("f-1.jpg", ContentFile(b"a"), save=True)
        gsocial = Image(title="S", slug="s-1", language="es", description="")
        gsocial.image.save("s-1.jpg", ContentFile(b"b"), save=True)

        post = Post.objects.create(author=self.user)
        post.set_current_language("es")
        post.title = "T"
        post.slug = "t"
        post.content = "c"
        post.featured_image_asset = gfeatured
        post.social_image_asset = gsocial
        post.save()

        self.assertEqual(post.get_social_image().name, gsocial.image.name)

    def test_get_mobile_image_prefers_mobile_asset(self):
        gfeatured = Image(title="F", slug="fm-1", language="es", description="")
        gfeatured.image.save("fm-1.jpg", ContentFile(b"a"), save=True)
        gmobile = Image(title="M", slug="m-1", language="es", description="")
        gmobile.image.save("m-1.jpg", ContentFile(b"c"), save=True)

        post = Post.objects.create(author=self.user)
        post.set_current_language("es")
        post.title = "T"
        post.slug = "t"
        post.content = "c"
        post.featured_image_asset = gfeatured
        post.mobile_image_asset = gmobile
        post.save()

        self.assertEqual(post.get_mobile_image().name, gmobile.image.name)

    def test_post_admin_finalize_staged_png_persists_featured_asset(self):
        request = RequestFactory().post(
            "/admin/posts/post/add/",
            {
                "language": "es",
                "featured_image_staging_id": "",
                "social_image_staging_id": "",
                "mobile_image_staging_id": "",
            },
        )
        request.user = self.user

        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc``\xf8\x0f"
            b"\x00\x01\x05\x01\x02\xa7^\xab?\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        staged = StagedUpload.objects.create(
            file=SimpleUploadedFile("featured.png", png_bytes, content_type="image/png"),
        )
        request.POST = request.POST.copy()
        request.POST["featured_image_staging_id"] = str(staged.pk)

        post = Post(author=self.user, status="published")
        post.set_current_language("es")

        class DummyPostForm(ModelForm):
            class Meta:
                model = Post
                fields = ()

        form = DummyPostForm(instance=post)
        form.cleaned_data = {
            "title": "Post con imagen",
            "slug": "post-con-imagen",
            "summary": "Resumen",
            "meta_description": "",
        }

        post_admin = PostAdmin(Post, admin.site)
        post_admin._apply_gallery_asset_staging_to_cleaned_data(request, form)

        self.assertIsNotNone(form.instance.featured_image_asset)
        self.assertTrue(form.instance.featured_image_asset.image.name.endswith("post-con-imagen-16_9.png"))


class PostContentBlockSummaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="summary-editor", password="p")
        self.post = Post.objects.create(author=self.user)

    def test_mini_post_requires_its_own_summary(self):
        block = PostContentBlock(
            post=self.post,
            language="es",
            heading="Una sección indexable",
            content="Contenido de la sección.",
        )

        with self.assertRaises(ValidationError) as error:
            block.clean()

        self.assertIn("summary", error.exception.message_dict)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), LANGUAGES=(("es", "Español"), ("en", "English")))
class PostPointsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="points-user", password="p")
        self.other_user = get_user_model().objects.create_user(username="author-user", password="p")
        self.config = SiteConfiguration.get_solo()
        self.config.post_points_enabled = True
        self.config.daily_post_points_budget = 10
        self.config.max_points_per_post_per_day = 5
        self.config.save()

        self.post = Post.objects.create(author=self.other_user, status="published")
        self.post.set_current_language("en")
        self.post.title = "Points post"
        self.post.slug = "points-post"
        self.post.content = "Body"
        self.post.save()

    def test_post_points_summary_counts_remaining_budget(self):
        PostPointAllocation.objects.create(user=self.user, post=self.post, points=3)
        summary = get_post_points_summary(self.user, self.post, self.config)

        self.assertEqual(summary.budget, 10)
        self.assertEqual(summary.assigned_today, 3)
        self.assertEqual(summary.current_post_points, 3)
        self.assertEqual(summary.remaining, 7)

    def test_authenticated_user_can_assign_points_to_post(self):
        self.client.force_login(self.user)

        with override("en"):
            response = self.client.post(
                reverse(
                    "posts:assign_post_points",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                ),
                {"points": 4},
            )

        self.assertEqual(response.status_code, 302)
        allocation = PostPointAllocation.objects.get(user=self.user, post=self.post)
        self.assertEqual(allocation.points, 4)

    def test_ajax_point_assignment_returns_updated_summary(self):
        self.client.force_login(self.user)

        with override("en"):
            response = self.client.post(
                reverse(
                    "posts:assign_post_points",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                ),
                {"points": 4},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["assigned_points"], 4)
        self.assertEqual(payload["remaining_points"], 6)
        self.assertEqual(payload["post_points_today_total"], 4)

    def test_ajax_assignment_returns_budget_error_without_creating_allocation(self):
        self.client.force_login(self.user)
        second_post = Post.objects.create(author=self.other_user, status="published")
        second_post.set_current_language("en")
        second_post.title = "Second post"
        second_post.slug = "second-post"
        second_post.content = "Body"
        second_post.save()

        PostPointAllocation.objects.create(user=self.user, post=second_post, points=8)

        with override("en"):
            response = self.client.post(
                reverse(
                    "posts:assign_post_points",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                ),
                {"points": 4},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "You only have 2 point(s) left for today.")
        self.assertFalse(PostPointAllocation.objects.filter(user=self.user, post=self.post).exists())

    def test_user_cannot_exceed_daily_budget(self):
        self.client.force_login(self.user)
        second_post = Post.objects.create(author=self.other_user, status="published")
        second_post.set_current_language("en")
        second_post.title = "Second post"
        second_post.slug = "second-post"
        second_post.content = "Body"
        second_post.save()

        PostPointAllocation.objects.create(user=self.user, post=second_post, points=8)

        with override("en"):
            response = self.client.post(
                reverse(
                    "posts:assign_post_points",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                ),
                {"points": 4},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You only have 2 point(s) left for today.")
        self.assertFalse(PostPointAllocation.objects.filter(user=self.user, post=self.post).exists())

    def test_author_sees_block_message_when_self_points_are_disabled(self):
        self.client.force_login(self.other_user)

        with override("en"):
            response = self.client.get(
                reverse(
                    "posts:post_detail",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot assign points to your own post.")
        self.assertNotContains(response, "Save points")

    def test_recent_account_cannot_assign_points_until_minimum_age(self):
        self.client.force_login(self.user)
        self.config.post_points_min_account_age_days = 3
        self.config.save()
        self.user.date_joined = timezone.now() - timedelta(days=1)
        self.user.save(update_fields=["date_joined"])

        with override("en"):
            response = self.client.post(
                reverse(
                    "posts:assign_post_points",
                    kwargs={
                        "year": self.post.published_date.year,
                        "month": self.post.published_date.month,
                        "day": self.post.published_date.day,
                        "slug": "points-post",
                    },
                ),
                {"points": 2},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "You can start assigning points after 3 day(s) on the site.")
        self.assertFalse(PostPointAllocation.objects.filter(user=self.user, post=self.post).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), LANGUAGES=(("es", "Español"), ("en", "English")))
class PostCommunityPicksTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(username="community-author", password="p")
        self.reader = get_user_model().objects.create_user(username="community-reader", password="p")

    def _create_post(self, slug, title, *, editor_rating=0):
        post = Post.objects.create(
            author=self.author,
            status="published",
            show_in_post_grids=True,
            editor_rating=editor_rating,
        )
        post.set_current_language("en")
        post.title = title
        post.slug = slug
        post.content = "Body"
        post.save()
        return post

    def test_community_picks_mix_recent_points_and_editor_rating(self):
        points_leader = self._create_post("points-leader", "Points leader", editor_rating=5)
        editor_supported = self._create_post("editor-supported", "Editor supported", editor_rating=80)

        PostPointAllocation.objects.create(
            user=self.reader,
            post=points_leader,
            points=3,
            date=timezone.localdate(),
        )
        PostPointAllocation.objects.create(
            user=self.author,
            post=editor_supported,
            points=2,
            date=timezone.localdate(),
        )

        posts = list(get_posts_for_list_type("community_picks"))

        self.assertEqual([post.pk for post in posts[:2]], [points_leader.pk, editor_supported.pk])
        self.assertEqual(posts[0].recent_points, 3)
        self.assertEqual(posts[0].community_score, 305)
        self.assertEqual(posts[1].recent_points, 2)
        self.assertEqual(posts[1].community_score, 280)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), LANGUAGES=(("es", "Español"), ("en", "English")))
class FollowingPostsViewTests(TestCase):
    def setUp(self):
        self.reader = get_user_model().objects.create_user(username="reader-following", password="p")
        self.author_a = get_user_model().objects.create_user(username="author-a", password="p")
        self.author_b = get_user_model().objects.create_user(username="author-b", password="p")

        self.followed_post = Post.objects.create(author=self.author_a, status="published")
        self.followed_post.set_current_language("en")
        self.followed_post.title = "Followed author post"
        self.followed_post.slug = "followed-author-post"
        self.followed_post.content = "Body"
        self.followed_post.save()

        self.other_post = Post.objects.create(author=self.author_b, status="published")
        self.other_post.set_current_language("en")
        self.other_post.title = "Other author post"
        self.other_post.slug = "other-author-post"
        self.other_post.content = "Body"
        self.other_post.save()

    def test_following_posts_view_only_shows_followed_authors_posts(self):
        UserFollow.objects.create(follower=self.reader, followed=self.author_a)
        self.client.force_login(self.reader)

        response = self.client.get(reverse("posts:following_posts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Followed author post")
        self.assertNotContains(response, "Other author post")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), LANGUAGES=(("es", "Español"), ("en", "English")))
class PostFavoritesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="favorite-user", password="p")
        self.author = get_user_model().objects.create_user(username="favorite-author", password="p")

        self.post = Post.objects.create(author=self.author, status="published")
        self.post.set_current_language("en")
        self.post.title = "Favorite post"
        self.post.slug = "favorite-post"
        self.post.content = "Body"
        self.post.save()

    def test_toggle_post_favorite_creates_relation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "posts:toggle_post_favorite",
                kwargs={
                    "year": self.post.published_date.year,
                    "month": self.post.published_date.month,
                    "day": self.post.published_date.day,
                    "slug": "favorite-post",
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["is_favorited"])
        self.assertEqual(payload["favorites_total"], 1)
        self.assertTrue(PostFavorite.objects.filter(user=self.user, post=self.post).exists())

    def test_toggle_post_favorite_removes_relation(self):
        PostFavorite.objects.create(user=self.user, post=self.post)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "posts:toggle_post_favorite",
                kwargs={
                    "year": self.post.published_date.year,
                    "month": self.post.published_date.month,
                    "day": self.post.published_date.day,
                    "slug": "favorite-post",
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["is_favorited"])
        self.assertEqual(payload["favorites_total"], 0)
        self.assertFalse(PostFavorite.objects.filter(user=self.user, post=self.post).exists())

    def test_favorite_posts_view_only_shows_users_favorites(self):
        other_post = Post.objects.create(author=self.author, status="published")
        other_post.set_current_language("en")
        other_post.title = "Other post"
        other_post.slug = "other-post"
        other_post.content = "Body"
        other_post.save()

        PostFavorite.objects.create(user=self.user, post=self.post)
        self.client.force_login(self.user)

        response = self.client.get(reverse("posts:favorite_posts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Favorite post")
        self.assertNotContains(response, "Other post")

    def test_favoriting_a_post_creates_notification_for_author(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "posts:toggle_post_favorite",
                kwargs={
                    "year": self.post.published_date.year,
                    "month": self.post.published_date.month,
                    "day": self.post.published_date.day,
                    "slug": "favorite-post",
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        notification = UserNotification.objects.get(
            recipient=self.author,
            notification_type=UserNotification.NotificationType.POST_FAVORITED,
        )
        self.assertEqual(notification.actor, self.user)
        self.assertEqual(notification.related_post, self.post)
        self.assertIn("Favorite post", notification.message)

    def test_removing_favorite_does_not_create_new_notification(self):
        PostFavorite.objects.create(user=self.user, post=self.post)
        UserNotification.objects.create(
            recipient=self.author,
            actor=self.user,
            notification_type=UserNotification.NotificationType.POST_FAVORITED,
            title="New favorite on your post",
            message='favorite-user added your post "Favorite post" to favorites.',
            url=self.post.get_absolute_url(),
            related_post=self.post,
            dedupe_key=f"post-favorited:{self.post.id}:{self.user.id}:{self.author.id}",
        )
        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "posts:toggle_post_favorite",
                kwargs={
                    "year": self.post.published_date.year,
                    "month": self.post.published_date.month,
                    "day": self.post.published_date.day,
                    "slug": "favorite-post",
                },
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(
            UserNotification.objects.filter(
                recipient=self.author,
                notification_type=UserNotification.NotificationType.POST_FAVORITED,
            ).count(),
            1,
        )
