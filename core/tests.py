from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.language_urls import get_best_language_url, replace_language_prefix
from core.pagination import paginate_queryset
from pages.models import Page, PageSection


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
