"""Finalize staged uploads and duplicate gallery rows for new versions."""

from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

from gallery.asset_allocation import allocate_unique_asset_slug
from gallery.models import Image, StagedUpload


class FinalizationError(Exception):
    """Raised when staged/source finalization cannot complete."""


def finalize_image_from_staging(
    *,
    instance: Image,
    staged: StagedUpload,
    slug_input: str,
) -> None:
    """
    Copy staged bytes into ``gallery/{slug}.ext`` and assign ``instance.slug`` / ``instance.image``.

    Requires title and language on ``instance``. Description may be blank.
    """
    title = (instance.title or "").strip()
    lang = (instance.language or "").strip()
    if not title:
        raise FinalizationError("Title is required to finalize a staged upload.")
    if not lang:
        raise FinalizationError("Language is required to finalize a staged upload.")

    raw = (slug_input or "").strip()
    slug_base = slugify(raw)
    if not slug_base:
        raise FinalizationError("Slug is required to finalize a staged upload.")

    ext = Path(staged.file.name).suffix.lower() or ".jpg"
    final_slug, rel_path = allocate_unique_asset_slug(slug_base, ext)

    data = staged.file.read()
    if not data:
        raise FinalizationError("Staged file is empty.")

    default_storage.save(rel_path, ContentFile(data))
    instance.slug = final_slug
    instance.image.name = rel_path


def finalize_image_from_source(
    *,
    instance: Image,
    source: Image,
    slug_input: str,
) -> None:
    """Copy an existing gallery file to a new slug/path; sets ``derived_from``."""
    title = (instance.title or "").strip()
    lang = (instance.language or "").strip()
    if not title:
        raise FinalizationError("Title is required when creating a version from an existing image.")
    if not lang:
        raise FinalizationError("Language is required when creating a version from an existing image.")

    raw = (slug_input or "").strip()
    slug_base = slugify(raw)
    if not slug_base:
        raise FinalizationError("Slug is required when creating a version from an existing image.")

    if not source.image:
        raise FinalizationError("Source image has no file.")

    ext = Path(source.image.name).suffix.lower() or ".jpg"
    final_slug, rel_path = allocate_unique_asset_slug(slug_base, ext)

    with source.image.open("rb") as src:
        data = src.read()
    if not data:
        raise FinalizationError("Source file is empty.")

    default_storage.save(rel_path, ContentFile(data))
    instance.derived_from = source
    instance.slug = final_slug
    instance.image.name = rel_path


def assign_direct_upload_slug(instance: Image, *, slug_input: str, uploaded_name: str) -> None:
    """When saving a normal ImageField upload on add, allocate slug from user input."""
    raw = (slug_input or "").strip()
    if not raw:
        raise ValidationError({"slug_input": "Slug is required."})
    slug_base = slugify(raw)
    if not slug_base:
        raise ValidationError({"slug_input": "Enter a valid slug (letters or numbers)."})
    ext = Path(uploaded_name).suffix.lower() or ".jpg"
    final_slug, _rel = allocate_unique_asset_slug(slug_base, ext)
    instance.slug = final_slug
