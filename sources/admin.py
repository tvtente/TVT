from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from .models import Citation, Source


@admin.register(Source)
class SourceAdmin(TranslatableAdmin):
    list_display = (
        "display_title",
        "organisation",
        "source_type",
        "language",
        "status",
        "publication_date",
    )
    list_filter = ("source_type", "status", "language", "publication_date")
    search_fields = ("translations__title", "organisation", "translations__bibliographic_reference", "url")
    list_select_related = ()
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("title", "organisation", "source_type", "language", "status")}),
        (_("Publication data"), {
            "fields": (
                "publication_date",
                "url",
                "document_url",
                "localized_url",
                "bibliographic_reference",
            ),
        }),
        (_("Reader-facing explanation"), {"fields": ("summary",)}),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description=_("Title"))
    def display_title(self, obj):
        return obj.display_title


@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ("source", "content_label", "is_primary", "language", "order", "locator", "created_at")
    list_filter = ("is_primary", "language", "content_type")
    search_fields = ("source__title", "note", "locator")
    autocomplete_fields = ("source",)
    readonly_fields = ("created_at",)
    fields = (
        "source",
        "content_type",
        "object_id",
        "language",
        "is_primary",
        "order",
        "locator",
        "note",
        "created_at",
    )

    @admin.display(description=_("Content"))
    def content_label(self, obj):
        return str(obj.content_object) if obj.content_object else "—"
