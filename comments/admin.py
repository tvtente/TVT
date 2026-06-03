# File: comments/admin.py

import logging
from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Comment, CommentTranslation

logger = logging.getLogger(__name__)


class HasPendingSuggestionFilter(admin.SimpleListFilter):
    title = _("Pending suggestion")
    parameter_name = "has_pending"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("With pending suggestion")),
            ("no", _("Without pending suggestion")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(pending_content__isnull=True).exclude(pending_content="")
        if self.value() == "no":
            return queryset.filter(Q(pending_content__isnull=True) | Q(pending_content=""))
        return queryset


class CommentTranslationInline(admin.TabularInline):
    model = CommentTranslation
    extra = 0
    fields = (
        "language",
        "content",
        "source",
        "provider",
        "translated_by",
        "is_preferred",
        "is_approved",
        "pending_content",
        "pending_translated_by",
        "pending_created_at",
    )
    readonly_fields = ("pending_created_at",)


@admin.register(Comment)
class CommentAdmin(MPTTModelAdmin):
    """
    🧠 Admin panel for nested comments with moderation support.
    Inherits from MPTTModelAdmin to show threaded replies.
    """

    # 📋 Display in list view
    list_display = ('__str__', 'post', 'author_name', 'is_approved', 'pending_translation_count', 'created_at')
    list_display_links = ('__str__',)

    # 🎛️ Filters and editable fields
    list_filter = ('is_approved', 'created_at', 'post')
    list_editable = ('is_approved',)

    # 🔍 Search fields
    search_fields = ('content', 'author_name', 'author_email', 'user__username', 'post__slug')

    # 🔒 Read-only fields for integrity
    readonly_fields = ('post', 'parent', 'user', 'author_name', 'author_email', 'content', 'created_at')
    inlines = (CommentTranslationInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            pending_translation_total=Count(
                "translations",
                filter=Q(translations__pending_content__isnull=False) & ~Q(translations__pending_content=""),
                distinct=True,
            )
        )

    @property
    def mptt_level_indent(self):
        """
        🧩 Optional: control indentation in tree display.
        Could be dynamic via SiteConfiguration in the future.
        """
        return 20  # You can update this to pull from config if needed

    @admin.display(description=_("Pending translations"), ordering="pending_translation_total")
    def pending_translation_count(self, obj):
        return obj.pending_translation_total or 0

    def save_model(self, request, obj, form, change):
        """
        🧠 Logs changes and moderation actions.
        """
        super().save_model(request, obj, form, change)

        if not change:
            logger.info(f"🆕 New comment on '{obj.post}' by {obj.author_name or obj.user}")
        elif 'is_approved' in form.changed_data and obj.is_approved:
            logger.info(f"✅ Comment approved: id={obj.id} by {request.user}")


@admin.register(CommentTranslation)
class CommentTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "comment_excerpt",
        "comment_post",
        "language",
        "source",
        "is_approved",
        "is_preferred",
        "translated_by",
        "pending_suggestion_summary",
        "updated_at",
    )
    list_filter = ("language", "source", "is_approved", "is_preferred", HasPendingSuggestionFilter, "comment__post")
    search_fields = ("comment__content", "content", "pending_content", "translated_by__username", "pending_translated_by__username", "comment__post__slug")
    actions = ("approve_pending_suggestions", "reject_pending_suggestions")
    readonly_fields = (
        "comment_post",
        "original_comment_preview",
        "current_translation_preview",
        "pending_suggestion_preview",
        "provider",
        "translated_by",
        "pending_translated_by",
        "pending_created_at",
        "created_at",
        "updated_at",
    )
    fields = (
        "comment_post",
        "language",
        "source",
        "is_approved",
        "is_preferred",
        "original_comment_preview",
        "current_translation_preview",
        "pending_suggestion_preview",
        "provider",
        "translated_by",
        "pending_translated_by",
        "pending_created_at",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("comment__post", "translated_by", "pending_translated_by")

    @admin.display(description=_("Comment"))
    def comment_excerpt(self, obj):
        text = obj.comment.content.strip()
        return text if len(text) <= 90 else f"{text[:87]}..."

    @admin.display(description=_("Post"), ordering="comment__post")
    def comment_post(self, obj):
        return obj.comment.post

    @admin.display(description=_("Original comment"))
    def original_comment_preview(self, obj):
        return format_html("<div style='max-width: 44rem; white-space: pre-wrap;'>{}</div>", obj.comment.content)

    @admin.display(description=_("Current public translation"))
    def current_translation_preview(self, obj):
        if not obj.content:
            return _("No approved content yet.")
        return format_html("<div style='max-width: 44rem; white-space: pre-wrap;'>{}</div>", obj.content)

    @admin.display(description=_("Pending suggestion"))
    def pending_suggestion_preview(self, obj):
        if not obj.pending_content:
            return _("No pending suggestion.")
        return format_html("<div style='max-width: 44rem; white-space: pre-wrap;'>{}</div>", obj.pending_content)

    @admin.display(boolean=True, description=_("Pending suggestion"))
    def has_pending_suggestion(self, obj):
        return bool(obj.pending_content)

    @admin.display(description=_("Pending review"))
    def pending_suggestion_summary(self, obj):
        if not obj.pending_content:
            return _("No")
        if obj.pending_translated_by:
            return _("Yes, by %(user)s") % {"user": obj.pending_translated_by.username}
        return _("Yes")

    @admin.action(description=_("Approve pending translation suggestions"))
    def approve_pending_suggestions(self, request, queryset):
        updated = 0
        for translation in queryset:
            if translation.approve_pending_suggestion():
                updated += 1
            elif not translation.is_approved:
                translation.is_approved = True
                translation.is_preferred = True
                translation.save(update_fields=["is_approved", "is_preferred", "updated_at"])
                updated += 1
        self.message_user(request, _("%(count)s translation(s) approved.") % {"count": updated})

    @admin.action(description=_("Reject pending translation suggestions"))
    def reject_pending_suggestions(self, request, queryset):
        updated = 0
        for translation in queryset:
            if translation.reject_pending_suggestion():
                updated += 1
        self.message_user(request, _("%(count)s pending suggestion(s) rejected.") % {"count": updated})
