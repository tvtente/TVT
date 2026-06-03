import tempfile

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from gallery.models import Image
from publications.models import Publication


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PublicationViewsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="publication-author", password="p")

    def _create_publication(self, *, slug, title, is_published=True):
        publication = Publication.objects.create(is_published=is_published)
        publication.authors.add(self.author)
        publication.set_current_language("en")
        publication.title = title
        publication.slug = slug
        publication.abstract = f"{title} abstract"
        publication.save()
        return publication

    def test_publication_list_shows_only_published_items(self):
        visible = self._create_publication(slug="visible-publication", title="Visible publication")
        self._create_publication(
            slug="hidden-publication",
            title="Hidden publication",
            is_published=False,
        )

        response = self.client.get(reverse("publications:publication_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["publications"]), [visible])

    def test_publication_detail_renders_published_publication(self):
        publication = self._create_publication(slug="detail-publication", title="Detail publication")

        response = self.client.get(reverse("publications:publication_detail", kwargs={"slug": "detail-publication"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["publication"].pk, publication.pk)

    def test_publication_detail_returns_404_for_missing_publication(self):
        response = self.client.get(
            reverse("publications:publication_detail", kwargs={"slug": "missing-publication"})
        )

        self.assertEqual(response.status_code, 404)

    def test_publication_document_view_returns_404_when_attachment_is_missing(self):
        self._create_publication(slug="documentless-publication", title="Documentless publication")

        response = self.client.get(
            reverse("publications:publication_document", kwargs={"slug": "documentless-publication"})
        )

        self.assertEqual(response.status_code, 404)

    def test_publication_document_view_renders_when_attachment_exists(self):
        publication = self._create_publication(slug="document-publication", title="Document publication")
        publication.attachment = SimpleUploadedFile("document.pdf", b"%PDF-1.4 test")
        publication.save(update_fields=["attachment"])

        response = self.client.get(
            reverse("publications:publication_document", kwargs={"slug": "document-publication"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["publication"].pk, publication.pk)

    def test_publication_mobile_image_prefers_mobile_asset(self):
        featured = Image(title="Featured", slug="publication-featured", language="en", description="")
        featured.image.save("publication-featured.jpg", ContentFile(b"featured"), save=True)
        mobile = Image(title="Mobile", slug="publication-mobile", language="en", description="")
        mobile.image.save("publication-mobile.jpg", ContentFile(b"mobile"), save=True)

        publication = self._create_publication(slug="mobile-publication", title="Mobile publication")
        publication.featured_image_asset = featured
        publication.mobile_image_asset = mobile
        publication.save()

        self.assertEqual(publication.get_mobile_image().name, mobile.image.name)
