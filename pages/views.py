# pages/views.py
import logging

from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext, get_language

from categories.views import get_category_by_slug
from core.pagination import get_site_config_int, paginate_queryset
from .models import Page, PageSection

logger = logging.getLogger(__name__)


def build_page_detail_context(page):
    page_sections = (
        PageSection.objects.language(get_language())
        .filter(page=page, enabled=True)
        .select_related("widget_zone", "background_image", "linked_page")
        .prefetch_related("linked_page__translations", "linked_page__categories")
        .distinct()
    )
    has_page_sections = page_sections.exists()
    uses_modular_sections = has_page_sections
    show_default_page_body = not has_page_sections

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("pages:directory"), "label": gettext("Pages")},
        {"url": "", "label": page.translated_title},
    ]

    return {
        "page": page,
        "page_sections": page_sections,
        "has_page_sections": has_page_sections,
        "uses_modular_sections": uses_modular_sections,
        "show_default_page_body": show_default_page_body,
        "translatable_object": page,
        "breadcrumbs": breadcrumbs,
    }

def get_page_by_slug(page_slug):
    language = get_language()
    page = (
        Page.objects.language(language)
        .filter(status="published")
        .translated(language, slug=page_slug)
        .distinct()
        .first()
    )
    if page:
        return page

    candidate = (
        Page.objects.filter(status="published", translations__slug=page_slug)
        .prefetch_related("translations", "categories")
        .distinct()
        .first()
    )

    if candidate is None:
        raise Http404(gettext("Page not found."))

    return candidate


def page_detail_view(request, slug):
    page = get_page_by_slug(slug)
    context = build_page_detail_context(page)

    return render(request, 'pages/page_detail.html', context)

def pages_by_category_view(request, category_slug):
    """
    Displays a paginated list of published pages belonging
    to a specific category.
    """
    category = get_category_by_slug(category_slug)
    all_pages_in_category = (
        category.pages.language(get_language())
        .filter(status='published')
        .order_by('translations__title')
        .distinct()
    )

    items_per_page = get_site_config_int(
        "blog_items_per_page",
        9,
        logger=logger,
        warning_message="SiteConfiguration does not exist. Using default items per page.",
    )
    pages_list = paginate_queryset(
        all_pages_in_category,
        request.GET.get("page", 1),
        items_per_page,
    )

    context = {
        'category': category,
        'pages_list': pages_list, # Pasamos el objeto paginado
    }
    return render(request, 'pages/pages_by_category.html', context)


def pages_with_category_view(request):
    pages = (
        Page.objects.language(get_language())
        .filter(categories__isnull=False)
        .distinct()
    )

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": "", "label": gettext("Pages")},
    ]

    return render(request, "pages/page_directory.html", {
        "pages": pages,
        "breadcrumbs": breadcrumbs,
    })
