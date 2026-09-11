# File: publications/admin.py

import logging
import uuid

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from gallery.finalization import FinalizationError
from gallery.models import Image, StagedUpload
from gallery.staging_uploads import create_gallery_image_from_staged_upload

from .models import Publication
from sources.models import Citation


logger = logging.getLogger(__name__)
User = get_user_model()


class CitationInline(GenericTabularInline):
    """Structured sources used by this publication."""

    model = Citation
    extra = 0
    autocomplete_fields = ("source",)
    fields = ("source", "language", "is_primary", "order", "locator", "note")
    verbose_name = _("Citation")
    verbose_name_plural = _("Citations and sources")


def get_researcher_users_queryset():
    """
    Users eligible to be attached to scientific publications.

    This is based on the public/professional profile flag, not on auth groups.
    A Subscriber, Contributor, Admin, Author, etc. can participate in research
    if an admin marks their profile as is_researcher=True.
    """
    return (
        User.objects
        .filter(
            is_active=True,
            profile__is_researcher=True,
        )
        .select_related("profile")
        .order_by("username")
        .distinct()
    )


@admin.register(Publication)
class PublicationAdmin(TranslatableAdmin):
    """
    📚 Admin for multilingual Publication model using django-parler.
    Optimized for academic/research-style documents.
    """

    # 📋 Columns shown in list view
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

    # 🔍 Search in translations and DOI
    search_fields = (
        "translations__title",
        "translations__abstract",
        "translations__introduction",
        "translations__theoretical_framework",
        "translations__objectives_hypotheses",
        "translations__methodology",
        "translations__results",
        "translations__discussion",
        "translations__conclusions",
        "translations__references",
        "translations__annexes",
        "translations__meta_title",
        "translations__meta_description",
        "doi",
    )

    # 🧮 Select multiple authors and categories with UI
    filter_horizontal = (
        "authors",
        "categories",
    )

    inlines = (CitationInline,)

    # 🙈 Optional: hide auto fields and custom media pickers
    readonly_fields = (
        "created_at",
        "updated_at",
        "featured_image_picker",
        "social_image_picker",
        "mobile_image_picker",
    )

    # ✍️ Group fields in the form
    fieldsets = (
        (_("Main Information"), {
            "fields": (
                "title",
                "slug",
                "abstract",
            ),
            "description": _(
                "Basic identification and summary of the publication. "
                "The abstract should summarize objectives, methods, and key findings."
            ),
        }),
        (_("Scientific Structure"), {
            "fields": (
                "introduction",
                "theoretical_framework",
                "objectives_hypotheses",
                "methodology",
                "results",
                "discussion",
                "conclusions",
                "references",
                "annexes",
            ),
            "description": _(
                "Structured scientific sections replacing the old full content field."
            ),
        }),
        (_("Metadata & SEO"), {
            "fields": (
                "meta_title",
                "meta_description",
                "doi",
                "publication_date",
                "is_published",
            ),
        }),
        (_("Relations"), {
            "fields": (
                "authors",
                "categories",
            ),
            "description": _(
                "Only users marked as researchers in their profile can be selected as authors."
            ),
        }),
        (_("Media & Files"), {
            "fields": (
                "featured_image_picker",
                "social_image_picker",
                "mobile_image_picker",
                "attachment",
            ),
        }),
        (_("System Info"), {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": (
                "collapse",
            ),
        }),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Limit publication authors to users marked as researchers in their profile.

        The scientific participation flag is profile.is_researcher, not auth group.
        This allows any kind of user to participate in research if an admin marks
        them as researcher.
        """
        if db_field.name == "authors":
            kwargs["queryset"] = get_researcher_users_queryset()

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # 🧑‍🏫 Author display logic
    @admin.display(description=_("Authors"))
    def get_authors(self, obj):
        return ", ".join(
            [
                author.get_full_name() or author.username
                for author in obj.authors.all()
            ]
        )

    # 📂 Categories display logic
    @admin.display(description=_("Categories"))
    def get_categories(self, obj):
        language = get_language()
        name_field = f"name_{language}"

        return ", ".join(
            [
                getattr(category, name_field, category.name)
                for category in obj.categories.all()
            ]
        )

    def _asset_file(self, obj, field_name):
        """
        Returns the underlying file object for a gallery.Image FK stored
        in a translated field.
        """
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
        """
        Returns initial URL, caption and FK for a translated gallery asset.
        """
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
        """
        Builds a Media Library picker for a translated gallery.Image FK.

        field_name:
            featured_image_asset / social_image_asset / mobile_image_asset

        staging_field_name:
            featured_image_staging_id / social_image_staging_id / mobile_image_staging_id
        """
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

    @admin.display(description=_("Featured image — media library"))
    def featured_image_picker(self, obj):
        return self._gallery_picker_html(
            obj=obj,
            field_name="featured_image_asset",
            staging_field_name="featured_image_staging_id",
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
        """
        Resolves either:
        - a staged upload UUID, finalizing it into gallery.Image
        - an existing gallery.Image FK from the hidden picker field
        - an explicit empty value, clearing the asset

        Returns:
            (should_apply, selected_asset)
        """
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

        title = (cleaned.get("title") or "").strip() or "publication-image"
        slug = (cleaned.get("slug") or "").strip() or "publication-image"
        abstract = (cleaned.get("abstract") or "").strip()
        meta = (cleaned.get("meta_description") or "").strip()
        description = abstract or meta

        if slug_suffix:
            slug_input = f"{slug}-{slug_suffix}"
        else:
            slug_input = slug

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
        language = (
            request.GET.get("language")
            or request.POST.get("language")
            or getattr(request, "LANGUAGE_CODE", None)
            or "es"
        )
        obj.set_current_language(language)

        should_apply_featured, featured_asset = self._resolve_gallery_asset_from_post(
            request,
            form,
            field_name="featured_image_asset",
            staging_field_name="featured_image_staging_id",
        )

        if should_apply_featured:
            obj.featured_image_asset = featured_asset

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
            "%s Publication saved by %s: %s",
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
