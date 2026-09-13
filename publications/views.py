# File: publications/views.py

import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.utils.translation import override
from parler.utils.context import switch_language

from .models import Publication
from sources.models import Citation


logger = logging.getLogger(__name__)


PUBLICATION_ACCESS_GROUPS = (
    "Researcher",
    "Reviewer",
    "Admin",
    "Site Manager",
)


def publication_access_required(view_func):
    """Restrict scientific publications to the authorised CMS roles."""

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not user.is_superuser and not user.groups.filter(
            name__in=PUBLICATION_ACCESS_GROUPS
        ).exists():
            raise PermissionDenied(_("You do not have permission to access publications."))
        return view_func(request, *args, **kwargs)

    return wrapped_view


def get_available_translation_urls(obj):
    """
    Returns translated URLs for all languages where the object has a translation.
    """
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


@publication_access_required
def publication_list_view(request):
    """
    📚 Shows the list of published scientific publications to authorised users.
    """
    language = get_language()

    publications_queryset = (
        Publication.objects
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

    paginator = Paginator(publications_queryset, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": "", "label": _("Publications")},
    ]

    return render(
        request,
        "publications/publication_list.html",
        {
            "publications": page_obj.object_list,
            "page_obj": page_obj,
            "breadcrumbs": breadcrumbs,
            "title": _("Publications"),
            "meta_title": _("Scientific Publications"),
            "meta_description": _(
                "Research, essays, reports, and structured scientific documents published by TVTente."
            ),
        },
    )


@publication_access_required
def publication_detail_view(request, slug):
    """
    📘 Shows the detail of a single published scientific publication.

    If the publication exists in another language but not in the current one,
    renders a friendly language-unavailable page instead of a raw 404.
    """
    language = get_language()

    try:
        publication = (
            Publication.objects
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

    except Publication.DoesNotExist:
        candidate = (
            Publication.objects
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
            raise Http404(_("Publication not found."))

        # If the target language exists but the slug is different, redirect
        # to the correct translated URL.
        if candidate.has_translation(language):
            with override(language):
                with switch_language(candidate, language):
                    return redirect(candidate.get_absolute_url())

        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "publication",
                "object": candidate,
                "available_translations": get_available_translation_urls(candidate),
                "title": _("Publication not available in this language"),
                "meta_title": _("Publication not available in this language"),
                "meta_description": _(
                    "This publication exists, but it has not been translated into the selected language yet."
                ),
            },
            status=404,
        )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("publications:publication_list"), "label": _("Publications")},
        {
            "url": "",
            "label": publication.safe_translation_getter(
                "title",
                any_language=True,
            ),
        },
    ]

    citations = (
        Citation.objects
        .filter(
            content_type=ContentType.objects.get_for_model(Publication, for_concrete_model=False),
            object_id=publication.pk,
            language=language,
        )
        .select_related("source")
        .prefetch_related("source__translations")
        .order_by("order", "pk")
    )

    sections = [
        {
            "title": _("Introduction"),
            "content": publication.safe_translation_getter("introduction", any_language=False),
        },
        {
            "title": _("Theoretical framework"),
            "content": publication.safe_translation_getter("theoretical_framework", any_language=False),
        },
        {
            "title": _("Objectives and hypotheses"),
            "content": publication.safe_translation_getter("objectives_hypotheses", any_language=False),
        },
        {
            "title": _("Methodology"),
            "content": publication.safe_translation_getter("methodology", any_language=False),
        },
        {
            "title": _("Results"),
            "content": publication.safe_translation_getter("results", any_language=False),
        },
        {
            "title": _("Discussion"),
            "content": publication.safe_translation_getter("discussion", any_language=False),
        },
        {
            "title": _("Conclusions"),
            "content": publication.safe_translation_getter("conclusions", any_language=False),
        },
        {
            "title": _("Annexes"),
            "content": publication.safe_translation_getter("annexes", any_language=False),
        },
    ]

    # The legacy free-text bibliography remains visible only for publications
    # that have not been migrated to structured citations yet.
    if not citations:
        sections.insert(
            -1,
            {
                "title": _("References / Bibliography"),
                "content": publication.safe_translation_getter("references", any_language=False),
            },
        )

    context = {
        "publication": publication,
        "sections": sections,
        "citations": citations,
        "breadcrumbs": breadcrumbs,
        "translatable_object": publication,
        "title": publication.safe_translation_getter("title", any_language=True),
        "meta_title": publication.safe_translation_getter("meta_title", any_language=True),
        "meta_description": publication.safe_translation_getter("meta_description", any_language=True),
    }

    return render(
        request,
        "publications/publication_detail.html",
        context,
    )

@publication_access_required
def publication_document_view(request, slug):
    """
    📄 Shows the publication PDF/document in a free reading page.

    Important:
    This is a reading view, not a paid download system yet.
    True download protection requires private media storage or a gated download view.
    """
    language = get_language()

    publication = get_object_or_404(
        Publication.objects
        .language(language)
        .prefetch_related(
            "authors",
            "categories",
            "translations",
        ),
        translations__language_code=language,
        translations__slug=slug,
        is_published=True,
    )

    if not publication.attachment:
        raise Http404(_("Document not found."))

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("publications:publication_list"), "label": _("Publications")},
        {"url": publication.get_absolute_url(), "label": publication.safe_translation_getter("title", any_language=True)},
        {"url": "", "label": _("Document viewer")},
    ]

    return render(
        request,
        "publications/publication_document.html",
        {
            "publication": publication,
            "breadcrumbs": breadcrumbs,
            "translatable_object": publication,
            "title": _("Document viewer"),
            "meta_title": _("Document viewer"),
            "meta_description": _("Read the publication document online."),
        },
    )
