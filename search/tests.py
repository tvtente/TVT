from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from pages.models import Page
from posts.models import Post
from site_settings.models import SiteConfiguration


class SearchResultsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="search-author", password="p")
        self.config = SiteConfiguration.get_solo()
        self.config.search_pages_per_page = 1
        self.config.search_posts_per_page = 1
        self.config.save()

    def _create_page(self, *, slug, title, importance_order=99, status="published"):
        page = Page.objects.create(
            author=self.user,
            status=status,
            importance_order=importance_order,
        )
        page.set_current_language("en")
        page.title = title
        page.slug = slug
        page.content = f"{title} body"
        page.save()
        return page

    def _create_post(self, *, slug, title, status="published"):
        post = Post.objects.create(author=self.user, status=status)
        post.set_current_language("en")
        post.title = title
        post.slug = slug
        post.summary = f"{title} summary"
        post.content = f"{title} content"
        post.save()
        return post

    def test_search_combines_pages_and_posts_and_orders_pages_by_importance(self):
        top_page = self._create_page(slug="alpha-top", title="Alpha top", importance_order=1)
        second_page = self._create_page(slug="alpha-second", title="Alpha second", importance_order=5)
        matching_post = self._create_post(slug="alpha-post", title="Alpha post")
        self._create_page(slug="draft-page", title="Alpha draft", status="draft")
        self._create_post(slug="draft-post", title="Alpha hidden", status="draft")

        response = self.client.get(reverse("search:search_results"), {"q": "Alpha"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_results"], 3)
        self.assertEqual(
            [page.pk for page in response.context["page_results"].paginator.object_list],
            [top_page.pk, second_page.pk],
        )
        self.assertEqual(
            [post.pk for post in response.context["post_results"].paginator.object_list],
            [matching_post.pk],
        )

    def test_search_uses_independent_page_and_post_pagination(self):
        first_page = self._create_page(slug="beta-top", title="Beta top", importance_order=1)
        second_page = self._create_page(slug="beta-second", title="Beta second", importance_order=2)
        newer_post = self._create_post(slug="beta-new", title="Beta new")
        older_post = self._create_post(slug="beta-old", title="Beta old")
        older_post.published_date = newer_post.published_date.replace(year=newer_post.published_date.year - 1)
        older_post.save(update_fields=["published_date"])

        response = self.client.get(
            reverse("search:search_results"),
            {"q": "Beta", "p_page": 2, "p_post": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_results"].number, 2)
        self.assertEqual(response.context["post_results"].number, 2)
        self.assertEqual(list(response.context["page_results"].object_list), [second_page])
        self.assertEqual(list(response.context["post_results"].object_list), [older_post])
