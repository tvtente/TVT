from decimal import Decimal

from django.utils.translation import get_language

from .models import Book


CART_SESSION_KEY = "cart"


def get_cart(request):
    cart = request.session.get(CART_SESSION_KEY)
    if isinstance(cart, dict):
        return cart
    return {}


def save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def get_cart_count(request):
    cart = get_cart(request)
    total = 0

    for item in cart.values():
        if isinstance(item, dict):
            total += int(item.get("quantity", 0) or 0)
        else:
            total += 1

    return total


def book_is_purchasable(book):
    return bool(book.is_available_for_purchase())


def add_book_to_cart(request, book, quantity=1):
    if not book_is_purchasable(book):
        return False

    cart = get_cart(request)
    book_key = str(book.pk)
    existing = cart.get(book_key, {})
    current_quantity = 0

    if isinstance(existing, dict):
        current_quantity = int(existing.get("quantity", 0) or 0)

    cart[book_key] = {
        "quantity": max(1, current_quantity + int(quantity or 1)),
    }
    save_cart(request, cart)
    return True


def remove_book_from_cart(request, book_id):
    cart = get_cart(request)
    removed = cart.pop(str(book_id), None)
    save_cart(request, cart)
    return removed is not None


def clear_cart(request):
    save_cart(request, {})


def get_cart_items(request):
    cart = get_cart(request)
    language = get_language()
    book_ids = []

    for book_id in cart.keys():
        try:
            book_ids.append(int(book_id))
        except (TypeError, ValueError):
            continue

    books = (
        Book.objects.language(language)
        .filter(pk__in=book_ids, is_published=True)
        .prefetch_related("authors", "categories", "translations")
        .distinct()
    )
    books_by_id = {book.pk: book for book in books}

    items = []
    subtotal = Decimal("0.00")
    currency = None

    for book_id in book_ids:
        book = books_by_id.get(book_id)
        if not book:
            continue

        raw_item = cart.get(str(book_id), {})
        quantity = 1
        if isinstance(raw_item, dict):
            quantity = max(1, int(raw_item.get("quantity", 1) or 1))

        price = book.price or Decimal("0.00")
        line_total = price * quantity

        if currency is None:
            currency = book.currency

        items.append(
            {
                "book": book,
                "quantity": quantity,
                "unit_price": price,
                "line_total": line_total,
            }
        )
        subtotal += line_total

    return {
        "items": items,
        "count": sum(item["quantity"] for item in items),
        "subtotal": subtotal,
        "currency": currency,
    }
