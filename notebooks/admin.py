from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from .models import Notebook


class NotebookAdminForm(forms.ModelForm):
    class Meta:
        model = Notebook
        fields = "__all__"
        widgets = {
            "markdown_source": forms.Textarea(attrs={"rows": 22, "style": "font-family: monospace;"}),
            "trusted_html_fragment": forms.Textarea(
                attrs={"rows": 14, "style": "font-family: monospace;"}
            ),
            "abstract": forms.Textarea(attrs={"rows": 4}),
        }


@admin.register(Notebook)
class NotebookAdmin(TranslatableAdmin):
    form = NotebookAdminForm
    list_display = ("current_title", "status", "author", "published_at", "updated_at")
    list_filter = ("status", "author", "categories")
    list_editable = ("status",)
    search_fields = (
        "translations__title",
        "translations__abstract",
        "translations__markdown_source",
        "translations__keywords",
    )
    filter_horizontal = ("categories",)
    readonly_fields = ("created_at", "updated_at", "rendered_html_preview")
    fields = (
        "title",
        "slug",
        "author",
        "status",
        "published_at",
        "categories",
        "abstract",
        "markdown_source",
        "trusted_html_fragment",
        "rendered_html_preview",
        "source_notebook",
        "meta_title",
        "meta_description",
        "keywords",
        "created_at",
        "updated_at",
    )

    @admin.display(description=_("Title"))
    def current_title(self, obj):
        return obj.translated_title

    @admin.display(description=_("Rendered HTML preview"))
    def rendered_html_preview(self, obj):
        if not obj or not getattr(obj, "pk", None):
            return _("Save the notebook to generate the HTML preview.")
        html = obj.safe_translation_getter("rendered_html", any_language=False) or ""
        if not html:
            return _("No rendered HTML has been generated for this translation yet.")
        return format_html(
            '<div style="max-height: 26rem; overflow: auto; border: 1px solid #ddd; padding: 1rem;">{}</div>',
            html,
        )

