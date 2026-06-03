import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from accounts.models import Profile
from books.models import Book
from gallery.models import Image
from shop.models import Order, OrderItem


User = get_user_model()


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class BookDocumentAccessTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self._media_root)
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)
        self.addCleanup(lambda: shutil.rmtree(self._media_root, ignore_errors=True))

        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="test-pass-123",
        )
        self.author = User.objects.create_user(
            username="author",
            email="author@example.com",
            password="test-pass-123",
        )

        self.book = Book.objects.create(
            is_published=True,
            requires_purchase=True,
            allow_free_preview=True,
            price=Decimal("9.99"),
            currency="EUR",
            available_from=timezone.localdate(),
        )
        self.book.authors.add(self.author)

        self.book.set_current_language("en")
        self.book.title = "Test book"
        self.book.slug = "test-book"
        self.book.description = "Test description"
        self.book.full_pdf = SimpleUploadedFile(
            "test-book.pdf",
            b"%PDF-1.4 test full document",
            content_type="application/pdf",
        )
        self.book.save()

    def test_document_redirects_when_user_is_anonymous(self):
        with override("en"):
            response = self.client.get(
                reverse("books:book_document", kwargs={"slug": self.book.slug})
            )

        self.assertRedirects(response, self.book.get_absolute_url())

    def test_document_redirects_when_user_has_no_paid_order(self):
        self.client.force_login(self.user)

        with override("en"):
            response = self.client.get(
                reverse("books:book_document", kwargs={"slug": self.book.slug})
            )

        self.assertRedirects(response, self.book.get_absolute_url())

    def test_document_is_accessible_for_book_author(self):
        self.client.force_login(self.author)

        with override("en"):
            response = self.client.get(
                reverse("books:book_document", kwargs={"slug": self.book.slug})
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "books/book_reader.html")
        self.assertEqual(response.context["title"], "Full document")
        self.assertEqual(response.context["document_file"].name, self.book.get_full_pdf().name)

    def test_document_is_accessible_for_user_with_paid_order(self):
        order = Order.objects.create(
            user=self.user,
            full_name="Reader User",
            email=self.user.email,
            status=Order.Status.PAID,
            currency="EUR",
            subtotal=Decimal("9.99"),
            total=Decimal("9.99"),
        )
        OrderItem.objects.create(
            order=order,
            book=self.book,
            title_snapshot="Test book",
            quantity=1,
            unit_price=Decimal("9.99"),
            line_total=Decimal("9.99"),
        )

        self.client.force_login(self.user)

        with override("en"):
            response = self.client.get(
                reverse("books:book_document", kwargs={"slug": self.book.slug})
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "books/book_reader.html")
        self.assertEqual(response.context["title"], "Full document")
        self.assertEqual(response.context["document_file"].name, self.book.get_full_pdf().name)


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class BookAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-pass-123",
        )
        self.author = User.objects.create_user(
            username="author-admin",
            email="author-admin@example.com",
            password="test-pass-123",
            is_active=True,
        )
        self.profile = self.author.profile
        self.profile.is_researcher = False
        self.profile.is_contributor = False
        self.profile.set_current_language("es")
        self.profile.professional_title = "Investigadora"
        self.profile.save()

        self.book = Book.objects.create(
            is_published=True,
            publication_date=timezone.localdate(),
        )
        self.book.set_current_language("es")
        self.book.title = "Libro admin"
        self.book.slug = "libro-admin"
        self.book.save()
        self.book.authors.add(self.author)

        self.client.force_login(self.admin_user)

    def test_book_change_admin_renders_with_translated_profile_filters(self):
        response = self.client.get(
            reverse("admin:books_book_change", args=[self.book.pk])
        )

        self.assertEqual(response.status_code, 200)
        author_field = response.context["adminform"].form.fields["authors"]
        self.assertIn(self.author, author_field.queryset)


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish")))
class BookImageHelperTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self._media_root)
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)
        self.addCleanup(lambda: shutil.rmtree(self._media_root, ignore_errors=True))

    def test_get_mobile_image_prefers_mobile_asset(self):
        cover_image = Image.objects.create(
            title="Book cover",
            slug="book-cover",
            image=SimpleUploadedFile(
                "book-cover.jpg",
                b"cover-bytes",
                content_type="image/jpeg",
            ),
        )
        mobile_image = Image.objects.create(
            title="Book mobile",
            slug="book-mobile",
            image=SimpleUploadedFile(
                "book-mobile.jpg",
                b"mobile-bytes",
                content_type="image/jpeg",
            ),
        )
        book = Book.objects.create()
        book.set_current_language("es")
        book.title = "Libro con imagen"
        book.slug = "libro-con-imagen"
        book.cover_image_asset = cover_image
        book.mobile_image_asset = mobile_image
        book.save()

        self.assertEqual(book.get_mobile_image().name, mobile_image.image.name)
