import logging
import uuid

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from gallery.finalization import FinalizationError
from gallery.models import Image, StagedUpload
from gallery.staging_uploads import create_gallery_image_from_staged_upload

from .models import Book


logger = logging.getLogger(__name__)
User = get_user_model()


def get_book_author_users_queryset():
    return (
        User.objects
        .filter(is_active=True)
        .filter(
            Q(profile__is_researcher=True)
            | Q(profile__is_contributor=True)
            | Q(profile__translations__professional_title__gt="")
            | Q(profile__translations__headline__gt="")
            | Q(profile__translations__institution__gt="")
        )
        .select_related("profile")
        .order_by("username")
        .distinct()
    )


@admin.register(Book)
class BookAdmin(TranslatableAdmin):
    list_display = (
        "title",
        "get_authors",
        "is_published",
        "publication_date",
        "get_categories",
    )
    list_filter = (
        "is_published",
        "publication_date",
        "authors",
    )
    ordering = ("-publication_date",)
    date_hierarchy = "publication_date"
    search_fields = (
        "translations__title",
        "translations__subtitle",
        "translations__description",
        "translations__excerpt",
        "translations__table_of_contents",
        "translations__meta_title",
        "translations__meta_description",
        "isbn",
    )
    filter_horizontal = (
        "authors",
        "categories",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "cover_image_picker",
        "social_image_picker",
        "mobile_image_picker",
    )
    fieldsets = (
        (_("Main Information"), {
            "fields": (
                "title",
                "slug",
                "subtitle",
            ),
        }),
        (_("Editorial Content"), {
            "fields": (
                "excerpt",
                "description",
                "table_of_contents",
                "meta_title",
                "meta_description",
            ),
        }),
        (_("Commercial Metadata"), {
            "fields": (
                "isbn",
                "publication_date",
                "is_published",
                "price",
                "currency",
                "allow_free_preview",
                "requires_purchase",
                "available_from",
            ),
        }),
        (_("Relations"), {
            "fields": (
                "authors",
                "categories",
            ),
            "description": _(
                "Selectable authors are limited to active users with a professional profile or contributor/researcher flags."
            ),
        }),
        (_("Media & Files"), {
            "fields": (
                "cover_image_picker",
                "social_image_picker",
                "mobile_image_picker",
                "preview_pdf",
                "full_pdf",
            ),
        }),
        (_("System Info"), {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "authors":
            kwargs["queryset"] = get_book_author_users_queryset()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def _clean_translated_file(field_name):
            def cleaner(self):
                value = self.cleaned_data.get(field_name)
                return None if value is False else value
            return cleaner

        form.clean_preview_pdf = _clean_translated_file("preview_pdf")
        form.clean_full_pdf = _clean_translated_file("full_pdf")
        return form

    @admin.display(description=_("Authors"))
    def get_authors(self, obj):
        return ", ".join(
            [
                author.get_full_name() or author.username
                for author in obj.authors.all()
            ]
        )

    @admin.display(description=_("Categories"))
    def get_categories(self, obj):
        language = get_language()
        return ", ".join(
            [
                category.safe_translation_getter(
                    "name",
                    language_code=language,
                    any_language=True,
                )
                for category in obj.categories.all()
            ]
        )

    def _asset_file(self, obj, field_name):
        if not obj or not getattr(obj, "pk", None):
            return None

        asset = obj.safe_translation_getter(
            field_name,
            any_language=False,
        )
        file_obj = getattr(asset, "image", None) if asset else None

        if file_obj and getattr(file_obj, "name", ""):
            return file_obj

        return None

    def _asset_initial_data(self, obj, field_name):
        initial_url = ""
        initial_caption = ""
        initial_fk = ""

        asset_file = self._asset_file(obj, field_name)

        if asset_file and getattr(asset_file, "name", ""):
            try:
                initial_url = asset_file.url
            except (OSError, ValueError, NotImplementedError):
                logger.warning(
                    _("Failed to resolve the media asset preview URL in the admin."),
                    exc_info=True,
                )
                initial_url = ""

            asset = (
                obj.safe_translation_getter(
                    field_name,
                    any_language=False,
                )
                if obj
                else None
            )

            if asset:
                initial_fk = str(asset.pk)
                initial_caption = "{} ({})".format(
                    getattr(asset, "title", "") or getattr(asset, "slug", ""),
                    getattr(asset, "slug", ""),
                )

        return initial_url, initial_caption, initial_fk

    def _gallery_picker_html(self, obj, field_name, staging_field_name):
        initial_url, initial_caption, initial_fk = self._asset_initial_data(
            obj,
            field_name,
        )

        return format_html(
            '<input type="hidden" name="{}" value="" autocomplete="off">'
            '<input type="hidden" name="{}" value="{}" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="{}" '
            'data-fk-name="{}" '
            'data-initial-url="{}" data-initial-caption="{}"></div>',
            staging_field_name,
            field_name,
            initial_fk,
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
            staging_field_name,
            field_name,
            initial_url,
            initial_caption,
        )

    @admin.display(description=_("Cover image — media library"))
    def cover_image_picker(self, obj):
        return self._gallery_picker_html(
            obj=obj,
            field_name="cover_image_asset",
            staging_field_name="cover_image_staging_id",
        )

    @admin.display(description=_("Social image — media library"))
    def social_image_picker(self, obj):
        return self._gallery_picker_html(
            obj=obj,
            field_name="social_image_asset",
            staging_field_name="social_image_staging_id",
        )

    @admin.display(description=_("Mobile image — media library"))
    def mobile_image_picker(self, obj):
        return self._gallery_picker_html(
            obj=obj,
            field_name="mobile_image_asset",
            staging_field_name="mobile_image_staging_id",
        )

    @staticmethod
    def _uuid_from_post(raw):
        if not (raw or "").strip():
            return None

        try:
            return uuid.UUID(str(raw).strip())
        except ValueError:
            return None

    def _resolve_gallery_asset_from_post(
        self,
        request,
        form,
        *,
        field_name,
        staging_field_name,
        slug_suffix="",
    ):
        if not getattr(form, "cleaned_data", None):
            return False, None

        cleaned = form.cleaned_data
        stage_id = self._uuid_from_post(
            request.POST.get(staging_field_name)
        )

        if not stage_id:
            raw_fk = request.POST.get(field_name)

            if raw_fk is None:
                return False, None

            raw_fk = raw_fk.strip()

            if not raw_fk:
                return True, None

            try:
                return True, Image.objects.get(pk=int(raw_fk))
            except (TypeError, ValueError, Image.DoesNotExist):
                raise ValidationError(
                    _("Invalid media library image selection.")
                ) from None

        language = (
            request.GET.get("language")
            or request.POST.get("language")
            or getattr(request, "LANGUAGE_CODE", None)
            or "es"
        )

        title = (cleaned.get("title") or "").strip() or "book-image"
        slug = (cleaned.get("slug") or "").strip() or "book-image"
        excerpt = (cleaned.get("excerpt") or "").strip()
        meta = (cleaned.get("meta_description") or "").strip()
        description = excerpt or meta
        slug_input = f"{slug}-{slug_suffix}" if slug_suffix else slug

        try:
            created = create_gallery_image_from_staged_upload(
                title=title,
                description=description,
                language=language,
                slug_input=slug_input,
                staging_uuid=stage_id,
            )
            return True, created
        except StagedUpload.DoesNotExist:
            raise ValidationError(
                _("The staged upload expired or was already removed. Upload again."),
            ) from None
        except FinalizationError as exc:
            raise ValidationError(str(exc)) from exc

    def save_model(self, request, obj, form, change):
        should_apply_cover, cover_asset = self._resolve_gallery_asset_from_post(
            request,
            form,
            field_name="cover_image_asset",
            staging_field_name="cover_image_staging_id",
        )
        if should_apply_cover:
            obj.cover_image_asset = cover_asset

        should_apply_social, social_asset = self._resolve_gallery_asset_from_post(
            request,
            form,
            field_name="social_image_asset",
            staging_field_name="social_image_staging_id",
            slug_suffix="social",
        )
        if should_apply_social:
            obj.social_image_asset = social_asset

        should_apply_mobile, mobile_asset = self._resolve_gallery_asset_from_post(
            request,
            form,
            field_name="mobile_image_asset",
            staging_field_name="mobile_image_staging_id",
            slug_suffix="mobile",
        )
        if should_apply_mobile:
            obj.mobile_image_asset = mobile_asset

        logger.info(
            "%s Book saved by %s: %s",
            "🆕" if not change else "✏️",
            request.user.username,
            obj,
        )

        super().save_model(request, obj, form, change)

    class Media:
        css = {
            "all": (
                "gallery/admin/media_library_picker.css",
            ),
        }
        js = (
            "gallery/admin/media_library_picker.js",
        )
