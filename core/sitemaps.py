"""Public, Spanish-first XML sitemaps for search engines."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import override

from categories.models import Category
from pages.models import Page
from posts.models import Post, PostContentBlock


class PublicSitemap(Sitemap):
    protocol = "https"
    language = "es"

    def get_urls(self, page=1, site=None, protocol=None):
        """Always emit the configured public domain, never Django's example.com."""
        parsed_url = urlparse(
            str(getattr(settings, "PUBLIC_SITE_URL", "https://tvtente.com"))
        )
        public_site = Site(domain=parsed_url.netloc, name=parsed_url.netloc)
        return super().get_urls(
            page=page,
            site=public_site,
            protocol=parsed_url.scheme or self.protocol,
        )

    def _spanish_url(self, obj):
        return obj.get_absolute_url_for_language(self.language)


class PageSitemap(PublicSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return (
            Page.objects.filter(status="published", translations__language_code=self.language)
            .distinct()
            .order_by("-updated_at")
        )

    def location(self, obj):
        return self._spanish_url(obj)

    def lastmod(self, obj):
        return obj.updated_at


class PostSitemap(PublicSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return (
            Post.objects.filter(
                status="published",
                published_date__lte=timezone.now(),
                translations__language_code=self.language,
            )
            .distinct()
            .order_by("-updated_at")
        )

    def location(self, obj):
        return self._spanish_url(obj)

    def lastmod(self, obj):
        return obj.updated_at


class MiniPostSitemap(PublicSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return (
            PostContentBlock.objects.select_related("post", "image_asset")
            .filter(
                language=self.language,
                post__status="published",
                post__published_date__lte=timezone.now(),
                block_type=PostContentBlock.BlockType.CONTENT,
                image_asset__isnull=False,
                share_slug__gt="",
                short_code__gt="",
            )
            .exclude(heading="")
            .exclude(summary="")
            .exclude(content="")
            .order_by("post__updated_at", "order")
        )

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.post.updated_at


class CategorySitemap(PublicSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return (
            Category.objects.filter(
                is_visible=True,
                translations__language_code=self.language,
            )
            .distinct()
            .order_by("tree_id", "lft")
        )

    def location(self, obj):
        with override(self.language):
            return obj.get_posts_url()


public_sitemaps = {
    "pages": PageSitemap,
    "posts": PostSitemap,
    "mini-posts": MiniPostSitemap,
    "categories": CategorySitemap,
}
