from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils.translation import override

from posts.models import Post
from tags.admin import TagAdmin
from tags.models import Tag
from django.contrib.auth import get_user_model


class TagModelTests(TestCase):
    def test_get_slug_prefers_translated_slug_for_active_language(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = "english-slug"
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_slug(), "english-slug")

    def test_get_slug_falls_back_to_global_slug_when_translation_slug_is_missing(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = ""
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_slug(), "global-slug")

    def test_get_absolute_url_uses_active_language_slug(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = "english-slug"
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_absolute_url(), "/en/posts/tag/english-slug/")


class TagAdminDeletionImpactTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = TagAdmin(Tag, self.site)
        self.user = get_user_model().objects.create_user(username="tag-author", password="p")

    def _create_tag(self, slug, label):
        tag = Tag.objects.create(slug=slug)
        tag.set_current_language("en")
        tag.label = label
        tag.translated_slug = slug
        tag.save()
        return tag

    def _create_post(self, slug, title, tags):
        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("en")
        post.slug = slug
        post.title = title
        post.content = "Body"
        post.save()
        post.tags.set(tags)
        return post

    def test_deletion_impact_counts_related_posts_and_untagged_posts(self):
        tag_a = self._create_tag("a", "A")
        tag_b = self._create_tag("b", "B")
        self._create_post("only-a", "Only A", [tag_a])
        self._create_post("a-and-b", "A and B", [tag_a, tag_b])

        impact = self.admin._get_deletion_impact(Tag.objects.filter(pk=tag_a.pk))

        self.assertEqual(impact["tag_count"], 1)
        self.assertEqual(impact["related_posts_count"], 2)
        self.assertEqual(impact["untagged_posts_count"], 1)
