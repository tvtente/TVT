"""Shared staged-upload → gallery.Image finalization (used by posts and pages admin)."""

from __future__ import annotations

import uuid

from django.db import transaction

from gallery.finalization import FinalizationError, finalize_image_from_staging
from gallery.models import Image, StagedUpload


def create_gallery_image_from_staged_upload(
    *,
    title: str,
    description: str,
    language: str,
    slug_input: str,
    staging_uuid: uuid.UUID,
) -> Image:
    """Copy staged bytes into a new gallery.Image; deletes the staged row on success."""
    title = (title or "").strip()
    language = (language or "").strip()
    if not title:
        raise FinalizationError("Title is required to finalize a staged upload.")
    if not language:
        raise FinalizationError("Language is required to finalize a staged upload.")

    with transaction.atomic():
        staged = StagedUpload.objects.select_for_update().get(pk=staging_uuid)
        instance = Image(
            title=title[:100],
            description=(description or "").strip(),
            language=language,
        )
        finalize_image_from_staging(
            instance=instance,
            staged=staged,
            slug_input=(slug_input or "").strip() or "page-image",
        )
        instance.save()
        staged.delete()
    return instance
