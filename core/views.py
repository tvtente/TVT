# core/views.py
import logging
from pathlib import Path

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext, get_language
from books.cart import get_cart_items
from categories.models import Category
from core.pagination import paginate_queryset
from pages.models import Page, PageSection
from posts.models import Post
from pages.views import build_page_detail_context
from posts.selectors import get_posts_for_list_type, get_untranslated_post_cards
from shop.models import Order
from shop.services import create_provisional_order_from_request

# Get a logger instance for this module.
logger = logging.getLogger(__name__)

HOMEPAGE_POSTS_CATEGORY_SLUG = "fundamentos-de-la-prevencion-moderna"


def _get_homepage_posts_queryset():
    """Posts assigned to the editorial category selected for the homepage."""
    category = (
        Category.objects.filter(translations__slug=HOMEPAGE_POSTS_CATEGORY_SLUG)
        .distinct()
        .first()
    )
    if category is None:
        logger.warning(
            "Homepage post category '%s' was not found.",
            HOMEPAGE_POSTS_CATEGORY_SLUG,
        )
        return Post.objects.none()
    return Post.objects.filter(categories__in=category.get_descendants(include_self=True)).distinct()


def public_verification_file(request):
    """Entrega el fichero de verificación en la raíz sin alterar la portada."""
    verification_file = (
        Path(__file__).resolve().parent
        / "verification"
        / "uetr2lswk1zkn93fjne4k5hyfvlann.html"
    )
    return HttpResponse(
        verification_file.read_text(encoding="utf-8").strip(),
        content_type="text/html",
    )

def home(request):
    """
    Finds the page marked as the 'homepage' in the database and renders it.
    If no homepage is set, it displays a default view.
    """
    logger.info(f"Homepage requested by user: {request.user.username or 'Anonymous'}")

    homepage = None
    try:
        homepage = (
            Page.objects.language(get_language())
            .filter(
                is_homepage=True,
                status='published',
                translations__language_code=get_language(),
            )
            .distinct()
            .latest('updated_at')
        )
        logger.debug(f"Serving homepage: '{homepage.translated_title}' (ID: {homepage.id})")

    except Page.DoesNotExist:
        # This is a configuration warning, not an error. The site still works.
        logger.warning("No published page has been configured as the homepage. Serving a placeholder.")
        # The template itself handles displaying a user-friendly message.
        
    except Exception as e:
        # Catch any other unexpected database or logic errors.
        logger.error(
            f"An unexpected error occurred while fetching the homepage.",
            exc_info=True # Include the full traceback for debugging.
        )
        # In this case, homepage remains None, and the template will show a message.
        # A more robust solution might render a 500 error page.

    context = (
        build_page_detail_context(homepage)
        if homepage is not None
        else {
            "page": None,
            "page_sections": [],
            "has_page_sections": False,
            "uses_modular_sections": False,
            "show_default_page_body": False,
            "translatable_object": None,
            "breadcrumbs": [
                {
                    "url": "",
                    "label": gettext("Home"),
                },
            ],
        }
    )

    # Keep this pagination independent from any other paginated component that
    # may be configured on the homepage.  It is intentionally fixed at three
    # cards so the homepage always presents a balanced row of latest posts.
    homepage_posts_queryset = _get_homepage_posts_queryset()
    context["homepage_posts"] = paginate_queryset(
        get_posts_for_list_type().filter(pk__in=homepage_posts_queryset),
        request.GET.get("home_page"),
        3,
    )
    context["untranslated_post_cards"] = get_untranslated_post_cards(
        queryset=homepage_posts_queryset,
    )
    if homepage is not None:
        homepage_sections = context["page_sections"]
        carousel_section = homepage_sections.filter(
            section_type=PageSection.SectionType.HERO,
        ).first()
        context["homepage_posts_after_section_id"] = (
            carousel_section.pk
            if carousel_section is not None
            else homepage_sections.values_list("pk", flat=True).first()
        )

    return render(request, 'pages/page_detail.html', context)


def cart_detail(request):
    cart_summary = get_cart_items(request)

    context = {
        "cart_items": cart_summary["items"],
        "cart_count": cart_summary["count"],
        "cart_subtotal": cart_summary["subtotal"],
        "cart_currency": cart_summary["currency"],
        "breadcrumbs": [
            {"url": "/", "label": gettext("Home")},
            {"url": "", "label": gettext("Shopping cart")},
        ],
        "title": gettext("Shopping cart"),
        "meta_title": gettext("Shopping cart"),
        "meta_description": gettext(
            "Review the books you want to buy before continuing to checkout."
        ),
    }

    return render(request, "core/cart_detail.html", context)


def checkout_detail(request):
    cart_summary = get_cart_items(request)

    context = {
        "cart_items": cart_summary["items"],
        "cart_count": cart_summary["count"],
        "cart_subtotal": cart_summary["subtotal"],
        "cart_currency": cart_summary["currency"],
        "checkout_email": request.user.email if request.user.is_authenticated else "",
        "checkout_name": (
            request.user.get_full_name() if request.user.is_authenticated else ""
        ),
        "breadcrumbs": [
            {"url": "/", "label": gettext("Home")},
            {"url": "/cart/", "label": gettext("Shopping cart")},
            {"url": "", "label": gettext("Checkout")},
        ],
        "title": gettext("Checkout"),
        "meta_title": gettext("Checkout"),
        "meta_description": gettext(
            "Review your books and continue to the payment step."
        ),
    }

    return render(request, "core/checkout_detail.html", context)


def checkout_create_order(request):
    if request.method != "POST":
        raise Http404(gettext("Page not found."))

    order = create_provisional_order_from_request(request)
    if order is None:
        messages.warning(
            request,
            gettext("Your cart is empty. Add at least one book before creating an order."),
        )
        return redirect("cart_detail")

    messages.success(
        request,
        gettext("Your provisional order has been created successfully."),
    )
    return redirect("checkout_order_pending", reference=order.reference)


def checkout_order_pending(request, reference):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "items__book"),
        reference=reference,
    )

    if order.user_id:
        if not request.user.is_authenticated or (
            request.user.id != order.user_id and not request.user.is_staff
        ):
            raise Http404(gettext("Page not found."))

    context = {
        "order": order,
        "breadcrumbs": [
            {"url": "/", "label": gettext("Home")},
            {"url": "/cart/", "label": gettext("Shopping cart")},
            {"url": "/checkout/", "label": gettext("Checkout")},
            {"url": "", "label": gettext("Order created")},
        ],
        "title": gettext("Order created"),
        "meta_title": gettext("Order created"),
        "meta_description": gettext(
            "Your provisional order has been created and is ready for the payment step."
        ),
    }

    return render(request, "core/checkout_order_pending.html", context)


def checkout_payment_placeholder(request):
    if request.method != "POST":
        raise Http404(gettext("Page not found."))

    reference = request.POST.get("reference")
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "items__book"),
        reference=reference,
    )

    if order.user_id:
        if not request.user.is_authenticated or (
            request.user.id != order.user_id and not request.user.is_staff
        ):
            raise Http404(gettext("Page not found."))

    if order.status == Order.Status.PENDING_PAYMENT:
        order.status = Order.Status.PAYMENT_UNAVAILABLE
        order.save(update_fields=["status", "updated_at"])
        messages.warning(
            request,
            gettext(
                "The payment step is not available yet. Your order has been marked as payment unavailable."
            ),
        )
    elif order.status == Order.Status.PAYMENT_UNAVAILABLE:
        messages.info(
            request,
            gettext("This order is already marked as payment unavailable."),
        )
    else:
        messages.info(
            request,
            gettext("This order is no longer pending payment."),
        )

    return redirect("checkout_order_pending", reference=order.reference)
