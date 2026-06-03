from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from gallery.asset_allocation import allocate_slug_library_sync
from gallery.models import GALLERY_IMAGE_DEFAULT_LANGUAGE, Image


def _language_codes():
    return [language_code for language_code, _ in settings.LANGUAGES]


def _page_lang_has_featured_asset(page, language_code):
    """True when a gallery.Image is linked for this locale (including base FK for default LANGUAGE_CODE)."""
    asset = getattr(page, f"featured_image_asset_{language_code}", None)
    if asset is not None:
        f = getattr(asset, "image", None)
        if f and getattr(f, "name", ""):
            return True
    if language_code == settings.LANGUAGE_CODE:
        base = getattr(page, "featured_image_asset", None)
        if base is not None:
            f = getattr(base, "image", None)
            if f and getattr(f, "name", ""):
                return True
    return False


def _clean_title(value, fallback):
    title = (value or fallback or '').strip()
    return title[:100]


def _clean_description(value):
    return (value or '').strip()


def _page_consolidated_title_and_description(page):
    """Pick one canonical title/description for synced gallery rows (ES → CA → EN → fallback)."""
    title = ''
    for language_code in ('es', 'ca', 'en'):
        value = getattr(page, f'title_{language_code}', None) or ''
        if isinstance(value, str) and value.strip():
            title = value.strip()
            break
    if not title and getattr(page, 'title', None):
        title = (page.title or '').strip()

    description = ''
    for language_code in ('es', 'ca', 'en'):
        value = (
            getattr(page, f'abstract_{language_code}', '')
            or getattr(page, f'meta_description_{language_code}', '')
            or ''
        )
        if isinstance(value, str) and value.strip():
            description = value.strip()
            break
    if not description:
        description = (
            (getattr(page, 'abstract', None) or '')
            or (getattr(page, 'meta_description', None) or '')
        ).strip()

    return (
        _clean_title(title, 'page-image'),
        _clean_description(description),
    )


def register_gallery_image(
    file_field,
    title=None,
    description=None,
):
    """
    Legacy path-sync helper keyed by stored relative path (used by post/page signals).

    Updates title/description on each call; fills slug/language only when missing.
    Prefer explicit gallery.Image FK wiring in a later phase.
    """
    if not file_field:
        return None

    image_name = getattr(file_field, 'name', '')
    if not image_name:
        return None

    default_title = _clean_title(title, Path(image_name).stem)
    default_description = _clean_description(description)

    stem = Path(image_name).stem
    ext = Path(image_name).suffix.lower() or '.jpg'
    slug_root = slugify(stem) or slugify(default_title) or 'image'
    sync_slug = allocate_slug_library_sync(slug_root, ext)

    image, created = Image.objects.get_or_create(
        image=image_name,
        defaults={
            'title': default_title,
            'description': default_description,
            'slug': sync_slug,
            'language': GALLERY_IMAGE_DEFAULT_LANGUAGE,
        },
    )
    image.title = default_title
    image.description = default_description
    update_fields = ['title', 'description']
    if not image.slug:
        image.slug = allocate_slug_library_sync(slug_root, ext)
        update_fields.append('slug')
    if not image.language:
        image.language = GALLERY_IMAGE_DEFAULT_LANGUAGE
        update_fields.append('language')
    image.save(update_fields=update_fields)
    return image


def sync_page_featured_image(page):
    # Legacy Page direct-upload fields were removed; keep signature for compatibility.
    return []


def sync_all_content_images():
    from pages.models import Page

    synced = []
    for page in Page.objects.all().iterator():
        synced.extend(sync_page_featured_image(page))
    return synced
