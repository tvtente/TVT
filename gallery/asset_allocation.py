"""Allocate unique slugs and gallery paths for media library assets."""

from __future__ import annotations

from pathlib import Path

from django.core.files.storage import default_storage
from django.utils.text import slugify

from gallery.models import Image


def normalize_slug_base(value: str) -> str:
    base = slugify((value or "").strip())
    return base or "image"


def allocate_unique_asset_slug(base_slug: str, extension: str) -> tuple[str, str]:
    """
    Return (slug, relative_storage_path) for a NEW file written to storage.

    Ensures slug is unique among Image rows and ``gallery/{slug}{ext}`` is unused on storage.
    Uses numeric suffixes: slug, slug-1, slug-2, ...
    """
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = ext.lower()
    root = normalize_slug_base(base_slug)
    counter: int | None = None
    while True:
        slug_attempt = root if counter is None else f"{root}-{counter}"
        relative_path = f"gallery/{slug_attempt}{ext}"
        slug_taken = Image.objects.filter(slug=slug_attempt).exists()
        path_taken = default_storage.exists(relative_path)
        if not slug_taken and not path_taken:
            return slug_attempt, relative_path
        counter = 1 if counter is None else counter + 1


def allocate_slug_library_sync(stem_base: str, extension: str) -> str:
    """
    Legacy path-sync: choose a unique slug using only the Image table.

    Used when the file path is already fixed on disk (e.g. post/page sync).
    Does not check storage.exists — the caller owns the path.
    """
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = ext.lower()
    root = normalize_slug_base(stem_base)
    counter: int | None = None
    while True:
        slug_attempt = root if counter is None else f"{root}-{counter}"
        if not Image.objects.filter(slug=slug_attempt).exists():
            return slug_attempt
        counter = 1 if counter is None else counter + 1
