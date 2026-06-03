# File: gallery/admin.py
from django.contrib import admin
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from gallery.finalization import (
    FinalizationError,
    assign_direct_upload_slug,
    finalize_image_from_source,
    finalize_image_from_staging,
)
from gallery.forms import ImageAddForm, ImageChangeForm
from gallery.models import Image, StagedUpload
import logging

logger = logging.getLogger(__name__)


def _safe_image_url(image_field):
    if not image_field:
        return ""
    image_instance = getattr(image_field, "instance", None)
    if image_instance and hasattr(image_instance, "get_image_url"):
        return image_instance.get_image_url()
    try:
        return image_field.url
    except (ValueError, OSError, SuspiciousFileOperation):
        return ""


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    """Gallery images with Phase 1 admin media picker (staging / library / direct upload)."""

    list_display = (
        "image_preview",
        "title",
        "slug",
        "language",
        "short_description",
        "public_url",
        "uploaded_at",
    )
    list_filter = ("uploaded_at", "language")
    ordering = ("-uploaded_at",)
    search_fields = ("title", "description", "slug")
    change_list_template = "admin/gallery/image/change_list.html"

    def get_form(self, request, obj=None, change=False, **kwargs):
        if change:
            kwargs.setdefault("form", ImageChangeForm)
        else:
            kwargs.setdefault("form", ImageAddForm)
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj:
            return (
                (
                    None,
                    {
                        "fields": (
                            "title",
                            "description",
                            "language",
                            "slug",
                            "derived_from",
                            "image_readonly_preview",
                            "uploaded_at",
                        ),
                    },
                ),
            )
        return (
            (
                None,
                {
                    "fields": (
                        "title",
                        "description",
                        "language",
                        "slug_input",
                        "staging_id",
                        "source_image_id",
                        "image",
                        "media_picker_panel",
                    ),
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("slug", "derived_from", "uploaded_at", "image_readonly_preview")
        return ("media_picker_panel",)

    @admin.display(description=_("Library"))
    def media_picker_panel(self, obj):
        return format_html(
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="staging_id" data-source-name="source_image_id" '
            'data-file-name="image"></div>',
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
        )

    @admin.display(description=_("Preview"))
    def image_readonly_preview(self, obj):
        image_url = _safe_image_url(getattr(obj, "image", None) if obj else None)
        if not image_url:
            return "-"
        return format_html(
            '<img src="{}" alt="" style="max-width:360px;max-height:220px;object-fit:contain;border:1px solid #ddd;border-radius:4px;background:#f8f9fa;">',
            image_url,
        )

    def changelist_view(self, request, extra_context=None):
        view_mode = request.GET.get("view", "list")

        query = request.GET.copy()
        query["view"] = "grid"
        grid_query_string = query.urlencode()

        query = request.GET.copy()
        query["view"] = "list"
        list_query_string = query.urlencode()

        request.GET = request.GET.copy()
        request.GET.pop("view", None)

        extra_context = extra_context or {}
        extra_context.update(
            {
                "gallery_view_mode": view_mode,
                "gallery_grid_query_string": grid_query_string,
                "gallery_list_query_string": list_query_string,
            }
        )
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description=_("Preview"))
    def image_preview(self, obj):
        image_url = _safe_image_url(getattr(obj, "image", None))
        if not image_url:
            return "-"
        return format_html(
            '<img src="{}" alt="" style="width:72px;height:48px;object-fit:contain;border-radius:4px;">',
            image_url,
        )

    @admin.display(description=_("Public URL"))
    def public_url(self, obj):
        image_url = _safe_image_url(getattr(obj, "image", None) if obj else None)
        if not image_url:
            return "-"
        return format_html('<a href="{0}" target="_blank" rel="noopener">{0}</a>', image_url)

    @admin.display(description=_("Summary / Abstract"))
    def short_description(self, obj):
        text = (obj.description or "").strip()
        if len(text) > 72:
            return f"{text[:72]}..."
        return text or "-"

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            logger.info("Image '%s' (ID: %s) updated by %s.", obj.title, obj.id, request.user.username)
            return

        staging_id = form.cleaned_data.get("staging_id")
        source_id = form.cleaned_data.get("source_image_id")

        try:
            with transaction.atomic():
                if staging_id:
                    staged = StagedUpload.objects.select_for_update().get(pk=staging_id)
                    finalize_image_from_staging(
                        instance=obj,
                        staged=staged,
                        slug_input=form.cleaned_data["slug_input"],
                    )
                    super().save_model(request, obj, form, change)
                    staged.delete()
                elif source_id:
                    src = Image.objects.get(pk=source_id)
                    finalize_image_from_source(
                        instance=obj,
                        source=src,
                        slug_input=form.cleaned_data["slug_input"],
                    )
                    super().save_model(request, obj, form, change)
                else:
                    assign_direct_upload_slug(
                        obj,
                        slug_input=form.cleaned_data["slug_input"],
                        uploaded_name=form.cleaned_data["image"].name,
                    )
                    super().save_model(request, obj, form, change)
        except StagedUpload.DoesNotExist:
            raise ValidationError(
                _("The staged upload expired or was already removed. Upload again."),
            ) from None
        except FinalizationError as exc:
            raise ValidationError(str(exc)) from exc

        logger.info("New image '%s' (ID: %s) added by %s.", obj.title, obj.id, request.user.username)

    class Media:
        css = {"all": ("gallery/admin/media_library_picker.css",)}
        js = ("gallery/admin/media_library_picker.js",)
