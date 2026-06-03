from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_GET, require_POST

from comments.forms import CommentTranslationSuggestionForm
from comments.models import Comment
from comments.services import (
    CommentTranslationDisabled,
    CommentTranslationError,
    get_or_create_comment_translation,
)


@require_GET
def translate_comment_view(request, comment_id):
    comment = get_object_or_404(
        Comment.objects.filter(is_approved=True).prefetch_related("translations"),
        pk=comment_id,
    )
    target_language = request.GET.get("language") or get_language()

    if target_language == comment.language:
        return JsonResponse(
            {
                "ok": True,
                "content": comment.content,
                "language": comment.language,
                "source": "original",
                "cached": True,
            }
        )

    try:
        translation, created = get_or_create_comment_translation(
            comment,
            target_language,
            requested_by=request.user,
        )
    except CommentTranslationDisabled as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=409,
        )
    except CommentTranslationError as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc) or _("The requested translation could not be generated."),
            },
            status=400,
        )

    return JsonResponse(
        {
            "ok": True,
            "content": translation.content,
            "language": translation.language,
            "source": translation.source,
            "provider": translation.provider,
            "cached": not created,
        }
    )


@require_POST
def suggest_comment_translation_view(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "ok": False,
                "error": _("You need to log in to suggest a translation."),
            },
            status=403,
        )

    comment = get_object_or_404(
        Comment.objects.filter(is_approved=True).prefetch_related("translations"),
        pk=comment_id,
    )
    target_language = request.POST.get("language") or get_language()

    if target_language == comment.language:
        return JsonResponse(
            {
                "ok": False,
                "error": _("A translation must target a different language from the original comment."),
            },
            status=400,
        )

    form = CommentTranslationSuggestionForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "ok": False,
                "error": form.errors.get("content", [_("Invalid translation content.")])[0],
            },
            status=400,
        )

    auto_approve = request.user.is_staff
    translation = comment.translations.filter(language=target_language).first()
    if translation:
        status = translation.submit_human_suggestion(
            form.cleaned_data["content"],
            request.user,
            auto_approve=auto_approve,
        )
    else:
        translation = comment.translations.create(
            language=target_language,
            content=form.cleaned_data["content"] if auto_approve else "",
            source=comment.translations.model.Source.HUMAN,
            provider="",
            translated_by=request.user if auto_approve else None,
            is_approved=auto_approve,
            is_preferred=auto_approve,
        )
        status = translation.submit_human_suggestion(
            form.cleaned_data["content"],
            request.user,
            auto_approve=auto_approve,
        )

    return JsonResponse(
        {
            "ok": True,
            "content": translation.content,
            "language": translation.language,
            "source": translation.source,
            "translated_by": translation.translated_by_id,
            "pending_review": status == "pending",
            "message": (
                _("Thanks. Your translation suggestion is now awaiting moderation.")
                if status == "pending"
                else _("The translation was updated successfully.")
            ),
        }
    )
