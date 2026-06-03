import logging
import uuid

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_summernote.admin import SummernoteModelAdmin
from parler.admin import TranslatableAdmin, TranslatableStackedInline

from gallery.finalization import FinalizationError
from gallery.models import StagedUpload
from gallery.staging_uploads import create_gallery_image_from_staged_upload
from .models import Page, PageSection


logger = logging.getLogger(__name__)

_PAGE_LANG_FK_ATTR = {
    "es": "featured_image_asset_es",
    "en": "featured_image_asset_en",
    "ca": "featured_image_asset_ca",
}


class PageSectionInline(TranslatableStackedInline):
    model = PageSection
    fk_name = "page"
    extra = 0
    fields = (
        "internal_title",
        "section_type",
        "enabled",
        "order",
        "heading",
        "content",
        "button_text",
        "button_url",
        "widget_zone",
        "linked_page",
        "background_image",
        "background_style",
        "full_width",
        "show_separator_after",
    )
    ordering = ("order", "id")
    classes = ("collapse",)


@admin.register(Page)
class PageAdmin(SummernoteModelAdmin, TranslatableAdmin):
    inlines = (PageSectionInline,)
    list_display = (
        "current_title",
        "status",
        "is_homepage",
        "importance_order",
        "author",
        "display_categories_list",
    )
    list_editable = ("status", "is_homepage", "importance_order")
    list_filter = ("status", "author", "categories", "is_homepage")
    search_fields = (
        "translations__title",
        "translations__content",
        "translations__abstract",
        "translations__keywords",
        "translations__slug",
    )
    ordering = ("importance_order", "-updated_at")
    filter_horizontal = ("categories",)
    summernote_fields = ("content",)
    fieldsets = (
        (_("Core content"), {
            "fields": (
                "title",
                "slug",
                "content",
                "abstract",
                "keywords",
                "featured_image_media_picker_es",
                "featured_image_media_picker_en",
                "featured_image_media_picker_ca",
                "featured_image_asset_es",
                "featured_image_asset_en",
                "featured_image_asset_ca",
            )
        }),
        (_("SEO"), {
            "description": _(
                "SEO fields control previews in search engines and social metadata; they do not replace the public abstract."
            ),
            "fields": ("meta_title", "meta_description"),
        }),
        (_("Publishing"), {
            "fields": ("author", "status", "is_homepage", "importance_order", "categories"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations", "categories")

    @admin.display(description=_("Title"))
    def current_title(self, obj):
        return obj.translated_title

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj) or [])
        for name in (
            "featured_image_media_picker_es",
            "featured_image_media_picker_en",
            "featured_image_media_picker_ca",
        ):
            if name not in readonly:
                readonly.append(name)
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in (
            "featured_image_asset",
            "featured_image_asset_es",
            "featured_image_asset_en",
            "featured_image_asset_ca",
        ):
            field = form.base_fields.get(field_name)
            if field:
                field.widget = forms.HiddenInput()
                field.required = False
        return form

    def _picker_initial_attrs(self, obj, fk_name):
        if not obj or not getattr(obj, "pk", None):
            return "", ""
        asset = getattr(obj, fk_name, None)
        if asset is None:
            return "", ""
        f = getattr(asset, "image", None)
        if not f or not getattr(f, "name", ""):
            return "", ""
        try:
            url = f.url
        except (OSError, ValueError, NotImplementedError):
            logger.warning(
                _("Failed to resolve the media asset preview URL in the admin."),
                exc_info=True,
            )
            url = ""
        caption = "{} ({})".format(
            getattr(asset, "title", "") or getattr(asset, "slug", ""),
            getattr(asset, "slug", ""),
        )
        return url, caption

    def _render_page_media_picker(self, obj, code, label, fk_name, staging_name):
        stage_url = reverse("gallery_media:stage")
        images_url = reverse("gallery_media:image_list")
        initial_url, initial_caption = self._picker_initial_attrs(obj=obj, fk_name=fk_name)
        return format_html(
            '<div class="page-asset-picker-lang" data-page-language="{}">'
            '<strong>{} ({})</strong>'
            '<input type="hidden" name="{}" value="" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="{}" '
            'data-fk-name="{}" '
            'data-initial-url="{}" data-initial-caption="{}"></div>'
            "</div>",
            code,
            label,
            code,
            staging_name,
            stage_url,
            images_url,
            staging_name,
            fk_name,
            initial_url,
            initial_caption,
        )

    @admin.display(description=_("Media library picker [es]"))
    def featured_image_media_picker_es(self, obj):
        return self._render_page_media_picker(
            obj,
            "es", _("Spanish"), "featured_image_asset_es", "featured_image_asset_staging_es"
        )

    @admin.display(description=_("Media library picker [en]"))
    def featured_image_media_picker_en(self, obj):
        return self._render_page_media_picker(
            obj,
            "en", _("English"), "featured_image_asset_en", "featured_image_asset_staging_en"
        )

    @admin.display(description=_("Media library picker [ca]"))
    def featured_image_media_picker_ca(self, obj):
        return self._render_page_media_picker(
            obj,
            "ca", _("Catalan"), "featured_image_asset_ca", "featured_image_asset_staging_ca"
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name.startswith("featured_image_asset"):
            kwargs.setdefault("widget", forms.HiddenInput)
            kwargs.setdefault("required", False)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @staticmethod
    def _pick_translated(obj, base: str, lang: str):
        return (
            obj.safe_translation_getter(base, language_code=lang, any_language=False)
            or obj.safe_translation_getter(base, any_language=True)
            or "page"
        )

    def _finalize_page_featured_staging(self, request, obj):
        def parse_uuid(post_key: str):
            raw = (request.POST.get(post_key) or "").strip()
            if not raw:
                return None
            try:
                return uuid.UUID(raw)
            except ValueError:
                return None

        try:
            for lang, fk_attr in _PAGE_LANG_FK_ATTR.items():
                staging_id = parse_uuid(f"featured_image_asset_staging_{lang}")
                if not staging_id:
                    continue
                title = self._pick_translated(obj, "title", lang).strip()[:100]
                slug = self._pick_translated(obj, "slug", lang).strip()
                abstract = (
                    obj.safe_translation_getter("abstract", language_code=lang, any_language=False)
                    or obj.safe_translation_getter("abstract", any_language=True)
                    or ""
                ).strip()
                meta = (
                    obj.safe_translation_getter("meta_description", language_code=lang, any_language=False)
                    or obj.safe_translation_getter("meta_description", any_language=True)
                    or ""
                ).strip()
                description = abstract or meta
                img = create_gallery_image_from_staged_upload(
                    title=title,
                    description=description,
                    language=lang,
                    slug_input=slug,
                    staging_uuid=staging_id,
                )
                setattr(obj, fk_attr, img)
        except StagedUpload.DoesNotExist:
            raise ValidationError(
                _("The staged upload expired or was already removed. Upload again."),
            ) from None
        except FinalizationError as exc:
            raise ValidationError(str(exc)) from exc

    @admin.display(description=_("Categories"))
    def display_categories_list(self, obj):
        return ", ".join(
            category.safe_translation_getter("name", any_language=True)
            for category in obj.categories.all()
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._finalize_page_featured_staging(request, obj)
        if change:
            obj.save()

    class Media:
        css = {"all": ("gallery/admin/media_library_picker.css",)}
        js = (
            "gallery/admin/media_library_picker.js",
            "pages/admin/page_media_library_tabs.js",
        )

@admin.register(PageSection)
class PageSectionAdmin(SummernoteModelAdmin, TranslatableAdmin):
    list_display = (
        "current_title",
        "page",
        "section_type",
        "enabled",
        "order",
        "widget_zone",
        "background_style",
    )
    list_editable = ("enabled", "order")
    list_filter = ("enabled", "section_type", "background_style", "widget_zone", "full_width")
    search_fields = (
        "translations__internal_title",
        "translations__heading",
        "translations__content",
        "page__translations__title",
    )
    ordering = ("page", "order", "id")
    summernote_fields = ("content",)
    fieldsets = (
        (_("Section"), {
            "fields": ("page", "internal_title", "section_type", "enabled", "order"),
        }),
        (_("Content"), {
            "fields": ("heading", "content", "button_text", "button_url", "linked_page"),
        }),
        (_("Widgets and layout"), {
            "fields": (
                "widget_zone",
                "background_image",
                "background_style",
                "full_width",
                "show_separator_after",
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "translations",
            "page__translations",
            "linked_page__translations",
        )

    @admin.display(description=_("Internal Title"))
    def current_title(self, obj):
        return obj.translated_internal_title
