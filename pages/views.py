# pages/views.py
import logging

from django.conf import settings
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext, get_language, override
from parler.utils.context import switch_language

from categories.views import get_category_by_slug
from core.pagination import get_site_config_int, paginate_queryset
from .models import Page, PageSection
from sources.models import Citation

logger = logging.getLogger(__name__)


def _group_page_sections(page_sections):
    grouped = []
    sections = list(page_sections)
    idx = 0

    while idx < len(sections):
        current = sections[idx]
        next_section = sections[idx + 1] if idx + 1 < len(sections) else None

        if (
            current.section_type == PageSection.SectionType.PAGE
            and next_section is not None
            and next_section.section_type == PageSection.SectionType.PAGE
            and current.background_style == next_section.background_style
            and current.full_width == next_section.full_width
        ):
            grouped.append(
                {
                    "kind": "page_pair",
                    "sections": [current, next_section],
                    "anchor": current,
                }
            )
            idx += 2
            continue

        grouped.append(
            {
                "kind": "single",
                "sections": [current],
                "anchor": current,
            }
        )
        idx += 1

    return grouped


def build_page_detail_context(page, user=None):
    language = get_language()
    page_sections = (
        PageSection.objects.language(language)
        .filter(page=page, enabled=True, translations__language_code=language)
        .select_related("widget_zone", "background_image", "linked_page")
        .prefetch_related("linked_page__translations", "linked_page__categories")
        .distinct()
    )
    if user and user.is_authenticated:
        page_sections = page_sections.filter(
            Q(allowed_groups__isnull=True) | Q(allowed_groups__user=user)
        ).distinct()
    else:
        page_sections = page_sections.filter(allowed_groups__isnull=True)
    has_page_sections = page_sections.exists()
    uses_modular_sections = has_page_sections
    show_default_page_body = not has_page_sections
    page_section_groups = _group_page_sections(page_sections)

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("pages:directory"), "label": gettext("Pages")},
        {"url": "", "label": page.translated_title},
    ]

    citations = (
        Citation.objects
        .filter(
            content_type=ContentType.objects.get_for_model(Page, for_concrete_model=False),
            object_id=page.pk,
            language=language,
        )
        .select_related("source")
        .prefetch_related("source__translations")
        .order_by("order", "pk")
    )

    return {
        "page": page,
        "page_sections": page_sections,
        "page_section_groups": page_section_groups,
        "has_page_sections": has_page_sections,
        "uses_modular_sections": uses_modular_sections,
        "show_default_page_body": show_default_page_body,
        "translatable_object": page,
        "breadcrumbs": breadcrumbs,
        "citations": citations,
    }

def get_available_translation_urls(page):
    """Build direct links for every translated edition of a page."""
    available = []
    for language_code, language_label in settings.LANGUAGES:
        if not page.has_translation(language_code):
            continue
        with override(language_code):
            with switch_language(page, language_code):
                available.append({
                    "code": language_code,
                    "label": language_label,
                    "url": page.get_absolute_url(),
                })
    return available


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
    language = get_language()

    if not page.has_translation(language):
        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "page",
                "object": page,
                "available_translations": get_available_translation_urls(page),
                "title": gettext("Page not available in this language"),
                "meta_title": gettext("Page not available in this language"),
                "meta_description": gettext(
                    "This page exists, but it has not been translated into the selected language yet."
                ),
            },
            status=404,
        )

    translated_slug = page.safe_translation_getter(
        "slug", language_code=language, any_language=False,
    )
    if translated_slug != slug:
        with override(language):
            return redirect(page.get_absolute_url())

    context = build_page_detail_context(page, user=request.user)

    return render(request, 'pages/page_detail.html', context)

def pages_by_category_view(request, category_slug):
    """
    Displays a paginated list of published pages belonging
    to a specific category.
    """
    category = get_category_by_slug(category_slug)
    all_pages_in_category = (
        category.pages.language(get_language())
        .filter(status='published', translations__language_code=get_language())
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
        .filter(categories__isnull=False, translations__language_code=get_language())
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
