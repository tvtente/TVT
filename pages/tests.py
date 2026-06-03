import tempfile
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from books.models import Book
from gallery.models import Image
from pages.models import HomeSection, Page, PageSection
from posts.models import Post
from publications.models import Publication
from widgets.models import Widget, WidgetZone


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PageFeaturedImageDualReadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="p1", password="x")

    def test_get_featured_image_prefers_language_asset(self):
        g = Image(title="G", slug="g-page", language="es", description="")
        g.image.save("g-page.jpg", ContentFile(b"1"), save=True)

        page = Page.objects.create(
            author=self.user,
            status="published",
        )
        page.set_current_language("es")
        page.title = "Tes"
        page.slug = "tes"
        page.content = "c"
        page.featured_image_asset_es = g
        page.save()

        with translation.override("es"):
            self.assertEqual(page.get_featured_image().name, g.image.name)


class HomepageUniquenessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="home-keeper", password="x")

    def _create_page(self, slug, title, *, is_homepage=False):
        page = Page.objects.create(
            author=self.user,
            status="published",
            is_homepage=is_homepage,
        )
        page.set_current_language("en")
        page.title = title
        page.slug = slug
        page.content = f"{title} content"
        page.save()
        return page

    def test_saving_new_homepage_unsets_previous_homepage(self):
        first = self._create_page("home-one", "Home one", is_homepage=True)
        second = self._create_page("home-two", "Home two", is_homepage=True)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_homepage)
        self.assertTrue(second.is_homepage)

    def test_promoting_existing_page_to_homepage_unsets_previous_homepage(self):
        first = self._create_page("home-one", "Home one", is_homepage=True)
        second = self._create_page("home-two", "Home two", is_homepage=False)

        second.is_homepage = True
        second.save()

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_homepage)
        self.assertTrue(second.is_homepage)


class PageSectionRenderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="page-builder", password="x")

    def test_page_detail_renders_page_sections_for_non_homepage(self):
        page = Page.objects.create(author=self.user, status="published", is_homepage=False)
        page.set_current_language("en")
        page.title = "Builder page"
        page.slug = "builder-page"
        page.content = "Legacy content"
        page.save()

        section = PageSection.objects.create(page=page, section_type=PageSection.SectionType.CONTENT, enabled=True, order=1)
        section.set_current_language("en")
        section.internal_title = "Intro block"
        section.heading = "Intro heading"
        section.content = "<p>Section body</p>"
        section.save()

        response = self.client.get(reverse("pages:page_detail", kwargs={"slug": "builder-page"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Intro heading")
        self.assertContains(response, "Section body", html=False)
        self.assertNotContains(response, "Legacy content")

    def test_homepage_without_page_sections_renders_legacy_page_content_when_home_sections_are_missing(self):
        page = Page.objects.create(author=self.user, status="published", is_homepage=True)
        page.set_current_language("en")
        page.title = "Home"
        page.slug = "home"
        page.content = "Homepage content"
        page.save()

        response = self.client.get(reverse("pages:page_detail", kwargs={"slug": "home"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Homepage content")

    def test_homepage_without_page_sections_ignores_legacy_home_sections(self):
        page = Page.objects.create(author=self.user, status="published", is_homepage=True)
        page.set_current_language("en")
        page.title = "Home"
        page.slug = "home"
        page.content = "Homepage content"
        page.save()

        section = HomeSection.objects.create(enabled=True, order=1)
        section.set_current_language("en")
        section.title = "Legacy home section"
        section.content = "<p>Legacy modular content</p>"
        section.save()

        response = self.client.get(reverse("pages:page_detail", kwargs={"slug": "home"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Homepage content")
        self.assertNotContains(response, "Legacy modular content", html=False)

    def test_page_section_can_embed_another_page(self):
        source_page = Page.objects.create(author=self.user, status="published", is_homepage=False)
        source_page.set_current_language("en")
        source_page.title = "Embedded delivery"
        source_page.slug = "embedded-delivery"
        source_page.abstract = "Embedded abstract"
        source_page.content = "<p>Embedded page body</p>"
        source_page.save()

        host_page = Page.objects.create(author=self.user, status="published", is_homepage=False)
        host_page.set_current_language("en")
        host_page.title = "Host page"
        host_page.slug = "host-page"
        host_page.content = "Host legacy content"
        host_page.save()

        section = PageSection.objects.create(
            page=host_page,
            section_type=PageSection.SectionType.PAGE,
            linked_page=source_page,
            enabled=True,
            order=1,
        )
        section.set_current_language("en")
        section.internal_title = "Embedded section"
        section.content = "<p>Section intro</p>"
        section.save()

        response = self.client.get(reverse("pages:page_detail", kwargs={"slug": "host-page"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Embedded delivery")
        self.assertContains(response, "Embedded abstract")
        self.assertContains(response, "Embedded page body", html=False)
        self.assertContains(response, "Section intro", html=False)
        self.assertNotContains(response, "Host legacy content")


class PageSectionValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="page-section-validator", password="x")

    def _create_page(self, slug, title):
        page = Page.objects.create(author=self.user, status="published", is_homepage=False)
        page.set_current_language("en")
        page.title = title
        page.slug = slug
        page.content = f"{title} body"
        page.save()
        return page

    def test_page_section_type_requires_linked_page(self):
        host_page = self._create_page("host-page", "Host page")
        section = PageSection(
            page=host_page,
            section_type=PageSection.SectionType.PAGE,
            enabled=True,
            order=1,
        )
        section.set_current_language("en")
        section.internal_title = "Broken page section"

        with self.assertRaisesMessage(ValidationError, "Embedded page sections must select a linked page."):
            section.full_clean()

    def test_widget_section_types_require_widget_zone(self):
        host_page = self._create_page("host-page", "Host page")
        section = PageSection(
            page=host_page,
            section_type=PageSection.SectionType.HERO,
            enabled=True,
            order=1,
        )
        section.set_current_language("en")
        section.internal_title = "Broken hero section"

        with self.assertRaisesMessage(ValidationError, "Hero and widget-zone sections must select a widget zone."):
            section.full_clean()

    def test_page_section_cannot_embed_its_own_page(self):
        host_page = self._create_page("host-page", "Host page")
        section = PageSection(
            page=host_page,
            section_type=PageSection.SectionType.PAGE,
            linked_page=host_page,
            enabled=True,
            order=1,
        )
        section.set_current_language("en")
        section.internal_title = "Self embedded section"

        with self.assertRaisesMessage(ValidationError, "A page section cannot embed its own page."):
            section.full_clean()


class MigrateHomepageToPageSectionsCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="homepage-admin", password="x")
        HomeSection.objects.all().delete()
        PageSection.objects.all().delete()

    def test_command_copies_legacy_home_sections_to_page_sections(self):
        homepage = Page.objects.create(author=self.user, status="published", is_homepage=True)
        homepage.set_current_language("en")
        homepage.title = "Home"
        homepage.slug = "home"
        homepage.content = "Homepage body"
        homepage.save()

        zone = WidgetZone.objects.create(name="Hero Right", slug="homepage-hero-right")
        legacy = HomeSection.objects.create(
            enabled=True,
            order=3,
            widget_zone=zone,
            background_style=HomeSection.BackgroundStyle.NOTICE,
            full_width=True,
            show_separator_after=True,
        )
        legacy.set_current_language("en")
        legacy.title = "Legacy hero"
        legacy.content = "<p>Legacy hero content</p>"
        legacy.save()
        legacy.set_current_language("es")
        legacy.title = "Hero legado"
        legacy.content = "<p>Contenido heredado</p>"
        legacy.save()

        stdout = StringIO()
        call_command("migrate_homepage_to_page_sections", stdout=stdout)

        page_sections = list(homepage.page_sections.order_by("order", "id"))
        self.assertEqual(len(page_sections), 1)
        self.assertEqual(page_sections[0].section_type, PageSection.SectionType.HERO)
        self.assertEqual(page_sections[0].widget_zone, zone)
        self.assertEqual(page_sections[0].translated_internal_title, "Legacy hero")
        self.assertIn("Created sections: 1", stdout.getvalue())

    def test_command_injects_main_content_zone_before_legacy_sections(self):
        homepage = Page.objects.create(author=self.user, status="published", is_homepage=True)
        homepage.set_current_language("en")
        homepage.title = "Home"
        homepage.slug = "home"
        homepage.content = "Homepage body"
        homepage.save()

        main_zone = WidgetZone.objects.create(name="Main content", slug="homepage-main-content")
        Widget.objects.create(
            zone=main_zone,
            widget_type=Widget.WidgetType.RECENT_POSTS,
            title="Recent posts",
            order=1,
        )

        legacy = HomeSection.objects.create(enabled=True, order=5)
        legacy.set_current_language("en")
        legacy.title = "Legacy content"
        legacy.content = "<p>Legacy content</p>"
        legacy.save()

        call_command("migrate_homepage_to_page_sections")

        page_sections = list(homepage.page_sections.order_by("order", "id"))
        self.assertEqual(len(page_sections), 2)
        self.assertEqual(page_sections[0].widget_zone, main_zone)
        self.assertEqual(page_sections[0].section_type, PageSection.SectionType.WIDGET_ZONE)
        self.assertEqual(page_sections[1].translated_internal_title, "Legacy content")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomepageWidgetSimulationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="homepage-builder", password="x")

    def _create_homepage(self):
        homepage = Page.objects.create(author=self.user, status="published", is_homepage=True)
        homepage.set_current_language("en")
        homepage.title = "Home"
        homepage.slug = "home"
        homepage.content = "Legacy homepage body"
        homepage.save()
        return homepage

    def _create_post_with_image(self, slug, title, *, editor_rating=0):
        image = Image(title=title, slug=f"{slug}-image", language="en", description="")
        image.image.save(f"{slug}.jpg", ContentFile(b"img"), save=True)

        post = Post.objects.create(
            author=self.user,
            status="published",
            show_in_post_grids=True,
            editor_rating=editor_rating,
        )
        post.set_current_language("en")
        post.title = title
        post.slug = slug
        post.summary = f"{title} summary"
        post.content = f"{title} content"
        post.featured_image_asset = image
        post.save()
        return post

    def _create_book(self, slug, title):
        book = Book.objects.create(is_published=True)
        book.authors.add(self.user)
        book.set_current_language("en")
        book.title = title
        book.slug = slug
        book.description = f"{title} description"
        book.save()
        return book

    def _create_publication(self, slug, title):
        publication = Publication.objects.create(is_published=True)
        publication.authors.add(self.user)
        publication.set_current_language("en")
        publication.title = title
        publication.slug = slug
        publication.abstract = f"{title} abstract"
        publication.save()
        return publication

    def test_homepage_renders_new_widgets_inside_page_sections(self):
        homepage = self._create_homepage()

        hero_zone = WidgetZone.objects.create(name="Homepage Hero", slug="homepage-hero")
        books_zone = WidgetZone.objects.create(name="Homepage Books", slug="homepage-books")
        publications_zone = WidgetZone.objects.create(
            name="Homepage Publications",
            slug="homepage-publications",
        )

        Widget.objects.create(
            zone=hero_zone,
            widget_type=Widget.WidgetType.HERO_CAROUSEL,
            title="Hero widget",
            section_title="Featured debates",
            cache_timeout=0,
            item_count=3,
            order=1,
        )
        Widget.objects.create(
            zone=books_zone,
            widget_type=Widget.WidgetType.BOOK_GRID_RECENT,
            title="Books widget",
            section_title="Recent books",
            view_all_link_text="See all books",
            view_all_link_url="/books/",
            cache_timeout=0,
            item_count=3,
            order=1,
        )
        Widget.objects.create(
            zone=publications_zone,
            widget_type=Widget.WidgetType.PUBLICATION_GRID_RECENT,
            title="Publications widget",
            section_title="Recent publications",
            view_all_link_text="See all publications",
            view_all_link_url="/publications/",
            cache_timeout=0,
            item_count=3,
            order=1,
        )

        hero_section = PageSection.objects.create(
            page=homepage,
            section_type=PageSection.SectionType.HERO,
            widget_zone=hero_zone,
            enabled=True,
            order=1,
        )
        hero_section.set_current_language("en")
        hero_section.internal_title = "Hero"
        hero_section.heading = "Think with TVTente"
        hero_section.content = "<p>Critical reflection and featured content.</p>"
        hero_section.button_text = "Explore"
        hero_section.button_url = "/posts/"
        hero_section.save()

        books_section = PageSection.objects.create(
            page=homepage,
            section_type=PageSection.SectionType.WIDGET_ZONE,
            widget_zone=books_zone,
            enabled=True,
            order=2,
        )
        books_section.set_current_language("en")
        books_section.internal_title = "Books"
        books_section.heading = "Books and editorial work"
        books_section.save()

        publications_section = PageSection.objects.create(
            page=homepage,
            section_type=PageSection.SectionType.WIDGET_ZONE,
            widget_zone=publications_zone,
            enabled=True,
            order=3,
        )
        publications_section.set_current_language("en")
        publications_section.internal_title = "Publications"
        publications_section.heading = "Research and publications"
        publications_section.save()

        self._create_post_with_image("hero-post", "Hero article", editor_rating=95)
        self._create_book("recent-book", "Recent book")
        self._create_publication("recent-publication", "Recent publication")

        response = self.client.get(reverse("pages:page_detail", kwargs={"slug": "home"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Think with TVTente")
        self.assertContains(response, "Critical reflection and featured content.", html=False)
        self.assertContains(response, "hero-carousel")
        self.assertContains(response, "Hero article")
        self.assertContains(response, "Books and editorial work")
        self.assertContains(response, "Recent book")
        self.assertContains(response, "See all books")
        self.assertContains(response, "Research and publications")
        self.assertContains(response, "Recent publication")
        self.assertContains(response, "See all publications")
        self.assertNotContains(response, "Legacy homepage body")


class BootstrapModularHomepageCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="bootstrap-admin", password="x")

    def _create_homepage(self):
        homepage = Page.objects.create(author=self.user, status="published", is_homepage=True)
        homepage.set_current_language("en")
        homepage.title = "Home"
        homepage.slug = "home"
        homepage.content = "Homepage body"
        homepage.save()
        return homepage

    def test_command_creates_scaffold_zones_widgets_and_sections(self):
        homepage = self._create_homepage()

        call_command("bootstrap_modular_homepage")

        hero_zone = WidgetZone.objects.get(slug="homepage-hero")
        books_zone = WidgetZone.objects.get(slug="homepage-books")
        publications_zone = WidgetZone.objects.get(slug="homepage-publications")

        hero_widget = Widget.objects.get(zone=hero_zone, widget_type=Widget.WidgetType.HERO_CAROUSEL)
        books_widget = Widget.objects.get(zone=books_zone, widget_type=Widget.WidgetType.BOOK_GRID_RECENT)
        publications_widget = Widget.objects.get(
            zone=publications_zone,
            widget_type=Widget.WidgetType.PUBLICATION_GRID_RECENT,
        )

        self.assertEqual(hero_widget.item_count, 3)
        self.assertEqual(hero_widget.translated_section_title, "Featured debates")
        self.assertEqual(books_widget.view_all_link_url, "/books/")
        self.assertEqual(books_widget.translated_view_all_link_text, "See all books")
        self.assertEqual(publications_widget.view_all_link_url, "/publications/")

        homepage_sections = list(homepage.page_sections.order_by("order", "id"))
        self.assertEqual(len(homepage_sections), 3)
        self.assertEqual(homepage_sections[0].widget_zone, hero_zone)
        self.assertEqual(homepage_sections[0].section_type, PageSection.SectionType.HERO)
        self.assertEqual(homepage_sections[1].widget_zone, books_zone)
        self.assertEqual(homepage_sections[2].widget_zone, publications_zone)
        self.assertEqual(homepage_sections[0].translated_heading, "Think with TVTente")
        self.assertEqual(homepage_sections[1].translated_heading, "Books and editorial work")
        self.assertEqual(homepage_sections[2].translated_heading, "Research and publications")

    def test_command_is_idempotent_without_duplicate_sections_or_widgets(self):
        homepage = self._create_homepage()
        scaffold_slugs = [
            "homepage-hero",
            "homepage-books",
            "homepage-publications",
        ]

        call_command("bootstrap_modular_homepage")
        call_command("bootstrap_modular_homepage")

        self.assertEqual(WidgetZone.objects.filter(slug__in=scaffold_slugs).count(), 3)
        self.assertEqual(Widget.objects.filter(zone__slug__in=scaffold_slugs).count(), 3)
        self.assertEqual(homepage.page_sections.count(), 3)


class AddHomepageEmbeddedPageSectionCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="embedded-command-admin", password="x")

    def _create_page(self, slug, title, *, is_homepage=False):
        page = Page.objects.create(author=self.user, status="published", is_homepage=is_homepage)
        page.set_current_language("en")
        page.title = title
        page.slug = slug
        page.content = f"{title} content"
        page.save()
        return page

    def test_command_creates_embedded_page_section(self):
        homepage = self._create_page("home", "Home", is_homepage=True)
        linked = self._create_page("delivery-page", "Delivery page")

        call_command(
            "add_homepage_embedded_page_section",
            linked_page_slug="delivery-page",
            heading_en="Featured delivery",
        )

        section = homepage.page_sections.get(section_type=PageSection.SectionType.PAGE)
        self.assertEqual(section.linked_page, linked)
        self.assertEqual(section.translated_heading, "Featured delivery")
        self.assertEqual(section.order, 1)

    def test_command_updates_existing_embedded_section_without_duplicates(self):
        homepage = self._create_page("home", "Home", is_homepage=True)
        linked = self._create_page("delivery-page", "Delivery page")

        call_command("add_homepage_embedded_page_section", linked_page_slug="delivery-page")
        call_command(
            "add_homepage_embedded_page_section",
            linked_page_slug="delivery-page",
            order=7,
            heading_en="Updated heading",
        )

        self.assertEqual(homepage.page_sections.filter(linked_page=linked).count(), 1)
        section = homepage.page_sections.get(linked_page=linked)
        self.assertEqual(section.order, 7)
        self.assertEqual(section.translated_heading, "Updated heading")

    def test_command_rejects_embedding_homepage_into_itself(self):
        self._create_page("home", "Home", is_homepage=True)

        with self.assertRaisesMessage(CommandError, "The homepage cannot embed itself."):
            call_command(
                "add_homepage_embedded_page_section",
                linked_page_slug="home",
            )
