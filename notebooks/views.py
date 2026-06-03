from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.utils.translation import override
from parler.utils.context import switch_language

from .models import Notebook


def get_available_translation_urls(obj):
    available = []

    for language_code, language_label in settings.LANGUAGES:
        if not obj.has_translation(language_code):
            continue

        with override(language_code):
            with switch_language(obj, language_code):
                available.append(
                    {
                        "code": language_code,
                        "label": language_label,
                        "url": obj.get_absolute_url(),
                    }
                )

    return available


def notebook_list_view(request):
    language = get_language()
    notebooks_queryset = (
        Notebook.objects.language(language)
        .filter(
            status=Notebook.Status.PUBLISHED,
            translations__language_code=language,
        )
        .prefetch_related("categories", "translations")
        .select_related("author")
        .order_by("-published_at", "-created_at")
        .distinct()
    )

    paginator = Paginator(notebooks_queryset, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": "", "label": _("Research notebooks")},
    ]

    return render(
        request,
        "notebooks/notebook_list.html",
        {
            "notebooks": page_obj.object_list,
            "page_obj": page_obj,
            "breadcrumbs": breadcrumbs,
            "title": _("Research notebooks"),
            "meta_title": _("Research notebooks and editorial archive"),
            "meta_description": _(
                "Research notebooks with analysis, results, documentation, and critical reflection for academic reading and digital archiving."
            ),
        },
    )


def notebook_detail_view(request, slug):
    language = get_language()

    try:
        notebook = (
            Notebook.objects.language(language)
            .prefetch_related("categories", "translations")
            .select_related("author")
            .get(
                translations__language_code=language,
                translations__slug=slug,
                status=Notebook.Status.PUBLISHED,
            )
        )
    except Notebook.DoesNotExist:
        candidate = (
            Notebook.objects.filter(
                translations__slug=slug,
                status=Notebook.Status.PUBLISHED,
            )
            .prefetch_related("categories", "translations")
            .select_related("author")
            .distinct()
            .first()
        )

        if not candidate:
            raise Http404(_("Notebook not found."))

        if candidate.has_translation(language):
            with override(language):
                with switch_language(candidate, language):
                    return redirect(candidate.get_absolute_url())

        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "notebook",
                "object": candidate,
                "available_translations": get_available_translation_urls(candidate),
                "title": _("Notebook not available in this language"),
                "meta_title": _("Notebook not available in this language"),
                "meta_description": _(
                    "This notebook exists, but it has not been translated into the selected language yet."
                ),
            },
            status=404,
        )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("notebooks:notebook_list"), "label": _("Research notebooks")},
        {"url": "", "label": notebook.translated_title},
    ]

    return render(
        request,
        "notebooks/notebook_detail.html",
        {
            "notebook": notebook,
            "breadcrumbs": breadcrumbs,
            "translatable_object": notebook,
            "title": notebook.translated_title,
            "meta_title": notebook.safe_translation_getter("meta_title", any_language=True),
            "meta_description": notebook.safe_translation_getter(
                "meta_description",
                any_language=True,
            ),
        },
    )

