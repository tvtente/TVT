import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from books.models import Book


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Pending payment")
        PAYMENT_UNAVAILABLE = "payment_unavailable", _("Payment unavailable")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Reference"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="shop_orders",
        verbose_name=_("User"),
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Full name"),
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email"),
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        verbose_name=_("Status"),
    )
    currency = models.CharField(
        max_length=3,
        default="EUR",
        verbose_name=_("Currency"),
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Subtotal"),
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Total"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"{self.reference}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Order"),
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="order_items",
        verbose_name=_("Book"),
    )
    title_snapshot = models.CharField(
        max_length=250,
        verbose_name=_("Book title"),
    )
    subtitle_snapshot = models.CharField(
        max_length=300,
        blank=True,
        verbose_name=_("Book subtitle"),
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity"),
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Unit price"),
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Line total"),
    )

    class Meta:
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def __str__(self):
        return f"{self.title_snapshot} ({self.quantity})"
