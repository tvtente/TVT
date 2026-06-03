from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from parler.admin import (
    TranslatableAdmin,
    TranslatableModelForm,
    TranslatableTabularInline,
)

from .models import WidgetZone, Widget


class WidgetInlineForm(TranslatableModelForm):
    pass


class WidgetInline(TranslatableTabularInline):
    model = Widget
    form = WidgetInlineForm
    fields = (
        "title",
        "widget_type",
        "order",
        "item_count",
        "cache_timeout",
        "category_filter",
        "column_count",
        "image_format",
        "section_title",
        "view_all_link_text",
        "view_all_link_url",
        "carousel_interval_ms",
    )
    extra = 1
    ordering = ["order"]
    classes = ("collapse",)


@admin.register(WidgetZone)
class WidgetZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "widget_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WidgetInline]

    @admin.display(description=_("Number of Widgets"))
    def widget_count(self, obj):
        return obj.widgets.count()


@admin.register(Widget)
class WidgetAdmin(TranslatableAdmin):
    list_display = (
        "current_title",
        "zone",
        "widget_type",
        "order",
        "cache_timeout",
        "column_count",
        "image_format",
        "current_section_title",
        "current_view_all_link_text",
        "view_all_link_url",
        "carousel_interval_ms",
    )
    list_filter = ("zone", "widget_type", "image_format")
    list_editable = ("order", "zone", "cache_timeout", "image_format")
    search_fields = (
        "translations__title",
        "translations__section_title",
        "translations__view_all_link_text",
    )
    fields = (
        "title",
        "zone",
        "widget_type",
        "order",
        "item_count",
        "cache_timeout",
        "category_filter",
        "column_count",
        "image_format",
        "section_title",
        "view_all_link_text",
        "view_all_link_url",
        "carousel_interval_ms",
    )
    ordering = ("zone", "order")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description=_("Widget Title"))
    def current_title(self, obj):
        return obj.translated_title

    @admin.display(description=_("Section Title (Optional)"))
    def current_section_title(self, obj):
        return obj.translated_section_title

    @admin.display(description=_("View All Link Text"))
    def current_view_all_link_text(self, obj):
        return obj.translated_view_all_link_text
