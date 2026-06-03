# File: categories/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin
from mptt.forms import MPTTAdminForm
from parler.admin import TranslatableAdmin, TranslatableModelForm

from .models import Category


class CategoryAdminForm(MPTTAdminForm, TranslatableModelForm):
    pass


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin, DraggableMPTTAdmin):
    form = CategoryAdminForm
    list_display = ("tree_actions", "indented_title", "current_slug")
    list_display_links = ("indented_title",)
    search_fields = (
        "translations__name",
        "translations__description",
        "translations__slug",
    )
    mptt_level_indent = 20

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    @admin.display(description=_("Slug"))
    def current_slug(self, obj):
        return obj.safe_translation_getter("slug", any_language=True) or ""
