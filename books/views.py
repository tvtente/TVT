from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.utils.translation import override
from parler.utils.context import switch_language

from .models import Book
from .cart import add_book_to_cart, book_is_purchasable, remove_book_from_cart
from shop.models import Order


def get_available_translation_urls(obj):
    available = []

    for language_code, language_label in settings.LANGUAGES:
        if not obj.has_translation(language_code):
            continue

        with override(language_code):
            with switch_language(obj, language_code):
                available.append({
                    "code": language_code,
                    "label": language_label,
                    "url": obj.get_absolute_url(),
                })

    return available


def get_available_document_translation_urls(obj, *, field_name, url_name):
    available = []

    for language_code, language_label in settings.LANGUAGES:
        if not obj.has_translation(language_code):
            continue

        document_file = obj.safe_translation_getter(
            field_name,
            language_code=language_code,
            any_language=False,
        )
        if not document_file:
            continue

        with override(language_code):
            with switch_language(obj, language_code):
                available.append({
                    "code": language_code,
                    "label": language_label,
                    "url": reverse(url_name, kwargs={"slug": obj.slug}),
                })

    return available


def _get_published_book_or_language_fallback(request, slug, *, redirect_to_preview=False):
    language = get_language()

    try:
        return (
            Book.objects
            .language(language)
            .prefetch_related(
                "authors",
                "categories",
                "translations",
            )
            .get(
                translations__language_code=language,
                translations__slug=slug,
                is_published=True,
            )
        )
    except Book.DoesNotExist:
        candidate = (
            Book.objects
            .filter(
                translations__slug=slug,
                is_published=True,
            )
            .prefetch_related(
                "authors",
                "categories",
                "translations",
            )
            .distinct()
            .first()
        )

        if not candidate:
            raise Http404(_("Book not found."))

        if candidate.has_translation(language):
            with override(language):
                with switch_language(candidate, language):
                    if redirect_to_preview:
                        return redirect(candidate.get_preview_url())
                    return redirect(candidate.get_absolute_url())

        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "book",
                "unavailable_resource": "book",
                "object": candidate,
                "available_translations": get_available_translation_urls(candidate),
                "title": _("Book not available in this language"),
                "meta_title": _("Book not available in this language"),
                "meta_description": _(
                    "This book exists, but it has not been translated into the selected language yet."
                ),
            },
            status=404,
        )


def user_can_access_full_book(request, book):
    if not book.requires_purchase:
        return True

    user = request.user
    if not user.is_authenticated:
        return False

    if user.is_staff or book.authors.filter(pk=user.pk).exists():
        return True

    return Order.objects.filter(
        user=user,
        status=Order.Status.PAID,
        items__book=book,
    ).exists()


def book_list_view(request):
    language = get_language()

    books_queryset = (
        Book.objects
        .language(language)
        .filter(
            is_published=True,
            translations__language_code=language,
        )
        .prefetch_related(
            "authors",
            "categories",
            "translations",
        )
        .order_by("-publication_date")
        .distinct()
    )

    paginator = Paginator(books_queryset, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": "", "label": _("Books")},
    ]

    return render(
        request,
        "books/book_list.html",
        {
            "books": page_obj.object_list,
            "page_obj": page_obj,
            "breadcrumbs": breadcrumbs,
            "title": _("Books"),
            "meta_title": _("Books"),
            "meta_description": _(
                "Books, editorial works, and stable publications published by TVTente."
            ),
        },
    )


def book_detail_view(request, slug):
    book = _get_published_book_or_language_fallback(request, slug)
    if not isinstance(book, Book):
        return book

    language = get_language()
    current_preview_pdf = book.get_preview_pdf(language_code=language)
    current_full_pdf = book.get_full_pdf(language_code=language)
    preview_language_editions = get_available_document_translation_urls(
        book,
        field_name="preview_pdf",
        url_name="books:book_reader",
    )
    full_document_language_editions = get_available_document_translation_urls(
        book,
        field_name="full_pdf",
        url_name="books:book_document",
    )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("books:book_list"), "label": _("Books")},
        {"url": "", "label": book.safe_translation_getter("title", any_language=True)},
    ]

    return render(
        request,
        "books/book_detail.html",
        {
            "book": book,
            "breadcrumbs": breadcrumbs,
            "translatable_object": book,
            "current_preview_pdf": current_preview_pdf,
            "current_full_pdf": current_full_pdf,
            "preview_language_editions": preview_language_editions,
            "full_document_language_editions": full_document_language_editions,
            "book_is_purchasable": book_is_purchasable(book),
            "book_is_coming_soon": book.is_coming_soon(),
            "can_access_full_book": user_can_access_full_book(request, book),
            "title": book.safe_translation_getter("title", any_language=True),
            "meta_title": book.safe_translation_getter("meta_title", any_language=True),
            "meta_description": book.safe_translation_getter("meta_description", any_language=True),
        },
    )


def cart_add_view(request, book_id):
    if request.method != "POST":
        raise Http404(_("Page not found."))

    book = (
        Book.objects
        .prefetch_related("translations")
        .filter(pk=book_id, is_published=True)
        .first()
    )
    if not book:
        raise Http404(_("Book not found."))

    if add_book_to_cart(request, book):
        messages.success(
            request,
            _("The book was added to your cart."),
        )
    else:
        messages.warning(
            request,
            _("This book is not available for purchase yet."),
        )

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or book.get_absolute_url()
    return redirect(next_url)


def cart_remove_view(request, book_id):
    if request.method != "POST":
        raise Http404(_("Page not found."))

    if remove_book_from_cart(request, book_id):
        messages.success(
            request,
            _("The book was removed from your cart."),
        )
    else:
        messages.warning(
            request,
            _("That book was no longer in your cart."),
        )

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("cart_detail")
    return redirect(next_url)


def book_reader_view(request, slug):
    book = _get_published_book_or_language_fallback(
        request,
        slug,
        redirect_to_preview=True,
    )
    if not isinstance(book, Book):
        return book

    preview_pdf = book.get_preview_pdf(language_code=get_language())
    if not book.allow_free_preview or not preview_pdf:
        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "book",
                "unavailable_resource": "preview",
                "object": book,
                "available_translations": get_available_document_translation_urls(
                    book,
                    field_name="preview_pdf",
                    url_name="books:book_reader",
                ),
                "title": _("Book preview not available in this language"),
                "meta_title": _("Book preview not available in this language"),
                "meta_description": _(
                    "This book exists, but its preview is not available in the selected language."
                ),
            },
            status=404,
        )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("books:book_list"), "label": _("Books")},
        {"url": book.get_absolute_url(), "label": book.safe_translation_getter("title", any_language=True)},
        {"url": "", "label": _("Preview")},
    ]

    return render(
        request,
        "books/book_reader.html",
        {
            "book": book,
            "breadcrumbs": breadcrumbs,
            "document_file": preview_pdf,
            "translatable_object": book,
            "title": _("Book preview"),
            "meta_title": _("Book preview"),
            "meta_description": _("Read the book preview online."),
        },
    )


def book_document_view(request, slug):
    book = _get_published_book_or_language_fallback(request, slug)
    if not isinstance(book, Book):
        return book

    if not user_can_access_full_book(request, book):
        messages.warning(
            request,
            _("You need a completed purchase before accessing the full edition of this book."),
        )
        return redirect(book.get_absolute_url())

    full_pdf = book.get_full_pdf(language_code=get_language())
    if not full_pdf:
        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "book",
                "unavailable_resource": "full_document",
                "object": book,
                "available_translations": get_available_document_translation_urls(
                    book,
                    field_name="full_pdf",
                    url_name="books:book_document",
                ),
                "title": _("Book document not available in this language"),
                "meta_title": _("Book document not available in this language"),
                "meta_description": _(
                    "This book exists, but its full document is not available in the selected language."
                ),
            },
            status=404,
        )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("books:book_list"), "label": _("Books")},
        {"url": book.get_absolute_url(), "label": book.safe_translation_getter("title", any_language=True)},
        {"url": "", "label": _("Full document")},
    ]

    return render(
        request,
        "books/book_reader.html",
        {
            "book": book,
            "breadcrumbs": breadcrumbs,
            "document_file": full_pdf,
            "translatable_object": book,
            "title": _("Full document"),
            "meta_title": _("Full document"),
            "meta_description": _("Read the full book document online."),
        },
    )
