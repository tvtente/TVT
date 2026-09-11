import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from books.models import Book
from shop.models import Order


User = get_user_model()


@override_settings(BOOKS_FREE_ACCESS_ENABLED=True, LANGUAGES=(("es", "Spanish"),))
class FreeBookCheckoutTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self._media_root)
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)
        self.addCleanup(lambda: shutil.rmtree(self._media_root, ignore_errors=True))

        self.user = User.objects.create_user(
            username="free-reader",
            email="reader@example.com",
            password="test-pass-123",
        )
        self.book = Book.objects.create(
            is_published=True,
            requires_purchase=True,
            available_from=timezone.localdate(),
        )
        self.book.set_current_language("es")
        self.book.title = "Libro gratuito"
        self.book.slug = "libro-gratuito"
        self.book.full_pdf = SimpleUploadedFile(
            "libro-gratuito.pdf",
            b"%PDF-1.4 full document",
            content_type="application/pdf",
        )
        self.book.save()

    def test_checkout_grants_free_access_and_enables_full_document(self):
        self.client.force_login(self.user)
        with override("es"):
            self.client.post(
                reverse("books:cart_add", kwargs={"book_id": self.book.pk}),
            )
            response = self.client.post(reverse("checkout_create_order"))

            order = Order.objects.get(user=self.user)
            self.assertEqual(order.status, Order.Status.FREE_ACCESS)
            self.assertEqual(order.total, 0)
            self.assertRedirects(
                response,
                reverse("checkout_order_pending", kwargs={"reference": order.reference}),
            )

            document = self.client.get(
                reverse("books:book_document", kwargs={"slug": self.book.slug})
            )
        self.assertEqual(document.status_code, 200)

    def test_checkout_requires_an_authenticated_reader(self):
        response = self.client.get(reverse("checkout_detail"))
        self.assertEqual(response.status_code, 302)
