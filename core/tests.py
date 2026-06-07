import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.language_urls import get_best_language_url, replace_language_prefix
from core.pagination import paginate_queryset
from gallery.models import Image
from pages.models import Page, PageSection
from posts.models import Post
from publications.models import Publication


class LanguageUrlTests(TestCase):
    def test_replace_language_prefix_preserves_querystring(self):
        self.assertEqual(
            replace_language_prefix("/es/posts/latest/?page=2", "en"),
            "/en/posts/latest/?page=2",
        )

    def test_get_best_language_url_prefers_explicit_language_map(self):
        result = get_best_language_url(
            "/es/posts/latest/",
            "ca",
            language_urls={"ca": "/ca/articles/destacats/"},
        )
        self.assertEqual(result, "/ca/articles/destacats/")

    def test_get_best_language_url_falls_back_to_prefix_switch(self):
        result = get_best_language_url("/accounts/login/?next=/es/posts/", "en")
        self.assertEqual(result, "/en/accounts/login/?next=/es/posts/")


class PaginationTests(TestCase):
    def test_paginate_queryset_returns_first_page_for_invalid_page(self):
        page = paginate_queryset(list(range(30)), "invalid", 10)
        self.assertEqual(page.number, 1)
        self.assertEqual(list(page.object_list), list(range(10)))

    def test_paginate_queryset_returns_last_page_for_out_of_range_page(self):
        page = paginate_queryset(list(range(25)), "999", 10)
        self.assertEqual(page.number, 3)
        self.assertEqual(list(page.object_list), list(range(20, 25)))


class HomepageResolutionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="homepage-user", password="x")

    def test_home_route_renders_page_marked_as_homepage_with_sections(self):
        homepage = Page.objects.create(author=self.user, status="published", is_homepage=True)
        homepage.set_current_language("en")
        homepage.title = "Homepage"
        homepage.slug = "homepage"
        homepage.content = "Legacy homepage body"
        homepage.save()

        section = PageSection.objects.create(
            page=homepage,
            section_type=PageSection.SectionType.CONTENT,
            enabled=True,
            order=1,
        )
        section.set_current_language("en")
        section.internal_title = "Intro"
        section.heading = "Homepage heading"
        section.content = "<p>Homepage section body</p>"
        section.save()

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Homepage heading")
        self.assertContains(response, "Homepage section body", html=False)
        self.assertNotContains(response, "Legacy homepage body")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GalleryAssetCleanupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="asset-cleaner", password="x")

    def test_replacing_post_mobile_asset_removes_old_unused_gallery_image(self):
        old_image = Image(title="Old mobile", slug="old-mobile", language="en", description="")
        old_image.image.save("old-mobile.jpg", ContentFile(b"old"), save=True)
        old_image_name = old_image.image.name

        new_image = Image(title="New mobile", slug="new-mobile", language="en", description="")
        new_image.image.save("new-mobile.jpg", ContentFile(b"new"), save=True)

        post = Post.objects.create(author=self.user, status="published")
        post.set_current_language("en")
        post.title = "Mobile post"
        post.slug = "mobile-post"
        post.content = "Body"
        post.mobile_image_asset = old_image
        post.save()

        post.mobile_image_asset = new_image
        post.save()

        self.assertFalse(Image.objects.filter(pk=old_image.pk).exists())
        self.assertFalse(old_image.image.storage.exists(old_image_name))
        self.assertTrue(Image.objects.filter(pk=new_image.pk).exists())

    def test_clearing_publication_mobile_asset_removes_old_unused_gallery_image(self):
        mobile_image = Image(title="Publication mobile", slug="publication-mobile-old", language="en", description="")
        mobile_image.image.save("publication-mobile-old.jpg", ContentFile(b"old"), save=True)
        mobile_image_name = mobile_image.image.name

        publication = Publication.objects.create(is_published=True)
        publication.authors.add(self.user)
        publication.set_current_language("en")
        publication.title = "Publication"
        publication.slug = "publication"
        publication.abstract = "Abstract"
        publication.mobile_image_asset = mobile_image
        publication.save()

        publication.mobile_image_asset = None
        publication.save()

        self.assertFalse(Image.objects.filter(pk=mobile_image.pk).exists())
        self.assertFalse(mobile_image.image.storage.exists(mobile_image_name))
