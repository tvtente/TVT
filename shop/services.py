from django.db import transaction
from django.conf import settings
from django.utils.translation import get_language

from books.cart import clear_cart, get_cart_items

from .models import Order, OrderItem


@transaction.atomic
def create_provisional_order_from_request(request):
    cart_summary = get_cart_items(request)
    if not cart_summary["items"]:
        return None

    user = request.user if request.user.is_authenticated else None
    if user is None:
        return None

    is_free_access = getattr(settings, "BOOKS_FREE_ACCESS_ENABLED", True)
    order = Order.objects.create(
        user=user,
        full_name=user.get_full_name(),
        email=user.email,
        status=(Order.Status.FREE_ACCESS if is_free_access else Order.Status.PENDING_PAYMENT),
        currency=cart_summary["currency"] or "EUR",
        subtotal=0 if is_free_access else cart_summary["subtotal"],
        total=0 if is_free_access else cart_summary["subtotal"],
    )

    language = get_language()
    for item in cart_summary["items"]:
        book = item["book"]
        OrderItem.objects.create(
            order=order,
            book=book,
            title_snapshot=book.safe_translation_getter("title", language_code=language, any_language=True) or "",
            subtitle_snapshot=book.safe_translation_getter("subtitle", language_code=language, any_language=True) or "",
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            line_total=item["line_total"],
        )

    clear_cart(request)
    return order
