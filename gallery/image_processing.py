"""Optimisation helpers for uploads stored by the media library."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image as PillowImage
from PIL import ImageOps, UnidentifiedImageError


_PASSTHROUGH_EXTENSIONS = {".svg", ".gif", ".webp"}


def convert_upload_to_webp(upload, *, quality: int = 82):
    """Return an optimised WebP upload when the input is a static raster image.

    SVGs, GIFs (including animated files) and existing WebP uploads are kept as
    supplied.  Invalid image data is also left untouched so Django's ImageField
    validation can report the appropriate upload error.
    """
    name = getattr(upload, "name", "upload") or "upload"
    if Path(name).suffix.lower() in _PASSTHROUGH_EXTENSIONS:
        return upload

    try:
        upload.seek(0)
        with PillowImage.open(upload) as image:
            if getattr(image, "is_animated", False):
                upload.seek(0)
                return upload

            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=quality, method=6)
    except (OSError, UnidentifiedImageError, ValueError):
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass
        return upload

    stem = Path(name).stem or "image"
    return ContentFile(output.getvalue(), name=f"{stem}.webp")
