# File: gallery/models.py
from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from gallery.image_processing import convert_upload_to_webp

# Editorial default when language is omitted (legacy sync, programmatic creates).
GALLERY_IMAGE_DEFAULT_LANGUAGE = "es"


def _language_choices():
    return [(code, code) for code, _ in settings.LANGUAGES]


def staged_upload_to(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
        ext = ".bin"
    return f"gallery/_staging/{uuid.uuid4().hex}{ext}"


def gallery_image_upload_to(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".jpg"
    if instance.slug:
        return f"gallery/{instance.slug}{ext}"
    return f"gallery/{Path(filename).name}"


class Image(models.Model):
    """
    One row per language/version: title, optional description, language, slug, and file.
    Text is not stored as translated columns; versions are separate rows (optionally linked via derived_from).
    """

    title = models.CharField(max_length=100, verbose_name=_("Title"))
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("Used as the filename stem: gallery/{slug}.ext"),
    )
    language = models.CharField(
        max_length=7,
        choices=_language_choices(),
        default=GALLERY_IMAGE_DEFAULT_LANGUAGE,
        blank=False,
        null=False,
        verbose_name=_("Language"),
    )

    derived_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derived_versions",
        verbose_name=_("Derived from"),
        help_text=_("Optional source image when this row was created as a new version."),
    )

    image = models.ImageField(
        upload_to=gallery_image_upload_to,
        blank=True,
        null=True,
        max_length=255,
        verbose_name=_("Image"),
    )

    description = models.TextField(blank=True, verbose_name=_("Summary / Abstract"))

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded at"))

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = _("Image")
        verbose_name_plural = _("Images")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Direct uploads through the library admin are converted before the
        # ImageField writes them to permanent storage. Finalised staged files
        # are already committed and therefore are not processed a second time.
        if (
            self.image
            and not self.image._committed
            and getattr(self, "convert_to_webp_upload", True)
        ):
            self.image = convert_upload_to_webp(self.image.file)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("gallery:image_detail", args=[self.pk])

    def get_absolute_url_for_language(self, language_code):
        with override(language_code):
            return reverse("gallery:image_detail", args=[self.pk])

    def get_image_url(self):
        if not self.image:
            return ""
        try:
            return self.image.url
        except (ValueError, OSError, SuspiciousFileOperation):
            return ""


class StagedUpload(models.Model):
    """Temporary upload before a gallery.Image row is finalized (e.g. on admin save)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ImageField(upload_to=staged_upload_to, verbose_name=_("Staged file"))
    original_filename = models.CharField(max_length=255, blank=True)
    convert_to_webp = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gallery_staged_uploads",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Staged upload")
        verbose_name_plural = _("Staged uploads")

    def __str__(self):
        return f"{self.original_filename or self.pk}"

    def save(self, *args, **kwargs):
        # Staging is the normal upload path used by post, page and publication
        # pickers, so conversion here ensures the original raster file is never
        # persisted in the media library.
        if self.file and not self.file._committed and self.convert_to_webp:
            self.file = convert_upload_to_webp(self.file.file)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        stored_name = self.file.name if self.file else ""
        storage = self.file.storage if self.file else None
        super().delete(*args, **kwargs)
        if stored_name and storage:
            storage.delete(stored_name)
