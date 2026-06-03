from django.core.files.storage import default_storage
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from books.models import Book
from gallery.models import Image
from posts.models import Post
from publications.models import Publication


BookTranslation = Book._parler_meta.root_model
PublicationTranslation = Publication._parler_meta.root_model
PostTranslation = Post._parler_meta.root_model

FILE_REFERENCE_FIELDS = (
    (BookTranslation, "preview_pdf"),
    (BookTranslation, "full_pdf"),
    (Publication, "attachment"),
)

GALLERY_REFERENCE_FIELDS = (
    (BookTranslation, "cover_image_asset"),
    (BookTranslation, "social_image_asset"),
    (PublicationTranslation, "featured_image_asset"),
    (PublicationTranslation, "social_image_asset"),
    (PostTranslation, "featured_image_asset"),
    (PostTranslation, "social_image_asset"),
)


def _file_name(field_value):
    return getattr(field_value, "name", "") or ""


def _remember_old_values(instance, *, file_fields=(), asset_fields=()):
    if not getattr(instance, "pk", None):
        return

    value_fields = list(file_fields)
    value_fields.extend(f"{field_name}_id" for field_name in asset_fields)
    old_values = type(instance).objects.filter(pk=instance.pk).values(*value_fields).first()
    instance._cleanup_old_values = old_values or {}


def _is_file_still_referenced(file_name, *, exclude_model=None, exclude_pk=None):
    if not file_name:
        return False

    for model, field_name in FILE_REFERENCE_FIELDS:
        queryset = model.objects.filter(**{field_name: file_name})
        if exclude_model is model and exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        if queryset.exists():
            return True

    return False


def _delete_file_if_unused(file_name, *, exclude_model=None, exclude_pk=None):
    if not file_name:
        return
    if _is_file_still_referenced(
        file_name,
        exclude_model=exclude_model,
        exclude_pk=exclude_pk,
    ):
        return
    if default_storage.exists(file_name):
        default_storage.delete(file_name)


def _is_gallery_asset_still_referenced(asset_id, *, exclude_model=None, exclude_pk=None):
    if not asset_id:
        return False

    for model, field_name in GALLERY_REFERENCE_FIELDS:
        queryset = model.objects.filter(**{f"{field_name}_id": asset_id})
        if exclude_model is model and exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        if queryset.exists():
            return True

    return False


def _delete_gallery_asset_if_unused(asset_id, *, exclude_model=None, exclude_pk=None):
    if not asset_id:
        return
    if _is_gallery_asset_still_referenced(
        asset_id,
        exclude_model=exclude_model,
        exclude_pk=exclude_pk,
    ):
        return

    image = Image.objects.filter(pk=asset_id).first()
    if not image:
        return

    image_name = _file_name(image.image)
    image.delete()
    if image_name and default_storage.exists(image_name):
        default_storage.delete(image_name)


def _cleanup_changed_files(instance, file_fields):
    old_values = getattr(instance, "_cleanup_old_values", {})
    for field_name in file_fields:
        old_name = old_values.get(field_name) or ""
        new_name = _file_name(getattr(instance, field_name, None))
        if old_name and old_name != new_name:
            _delete_file_if_unused(
                old_name,
                exclude_model=type(instance),
                exclude_pk=instance.pk,
            )


def _cleanup_changed_assets(instance, asset_fields):
    old_values = getattr(instance, "_cleanup_old_values", {})
    for field_name in asset_fields:
        old_asset_id = old_values.get(f"{field_name}_id")
        new_asset_id = getattr(instance, f"{field_name}_id", None)
        if old_asset_id and old_asset_id != new_asset_id:
            _delete_gallery_asset_if_unused(
                old_asset_id,
                exclude_model=type(instance),
                exclude_pk=instance.pk,
            )


def _cleanup_deleted_instance_media(instance, *, file_fields=(), asset_fields=()):
    for field_name in file_fields:
        file_name = _file_name(getattr(instance, field_name, None))
        if file_name:
            _delete_file_if_unused(file_name)

    for field_name in asset_fields:
        asset_id = getattr(instance, f"{field_name}_id", None)
        if asset_id:
            _delete_gallery_asset_if_unused(asset_id)


@receiver(pre_save, sender=BookTranslation)
def remember_old_book_translation_media(sender, instance, **kwargs):
    _remember_old_values(
        instance,
        file_fields=("preview_pdf", "full_pdf"),
        asset_fields=("cover_image_asset", "social_image_asset"),
    )


@receiver(post_save, sender=BookTranslation)
def cleanup_replaced_book_translation_media(sender, instance, **kwargs):
    _cleanup_changed_files(instance, ("preview_pdf", "full_pdf"))
    _cleanup_changed_assets(instance, ("cover_image_asset", "social_image_asset"))


@receiver(post_delete, sender=BookTranslation)
def cleanup_deleted_book_translation_media(sender, instance, **kwargs):
    _cleanup_deleted_instance_media(
        instance,
        file_fields=("preview_pdf", "full_pdf"),
        asset_fields=("cover_image_asset", "social_image_asset"),
    )


@receiver(pre_save, sender=Publication)
def remember_old_publication_media(sender, instance, **kwargs):
    _remember_old_values(
        instance,
        file_fields=("attachment",),
    )


@receiver(post_save, sender=Publication)
def cleanup_replaced_publication_media(sender, instance, **kwargs):
    _cleanup_changed_files(instance, ("attachment",))


@receiver(post_delete, sender=Publication)
def cleanup_deleted_publication_media(sender, instance, **kwargs):
    _cleanup_deleted_instance_media(
        instance,
        file_fields=("attachment",),
    )


@receiver(pre_save, sender=PublicationTranslation)
def remember_old_publication_translation_assets(sender, instance, **kwargs):
    _remember_old_values(
        instance,
        asset_fields=("featured_image_asset", "social_image_asset"),
    )


@receiver(post_save, sender=PublicationTranslation)
def cleanup_replaced_publication_translation_assets(sender, instance, **kwargs):
    _cleanup_changed_assets(instance, ("featured_image_asset", "social_image_asset"))


@receiver(post_delete, sender=PublicationTranslation)
def cleanup_deleted_publication_translation_assets(sender, instance, **kwargs):
    _cleanup_deleted_instance_media(
        instance,
        asset_fields=("featured_image_asset", "social_image_asset"),
    )


@receiver(pre_save, sender=PostTranslation)
def remember_old_post_translation_assets(sender, instance, **kwargs):
    _remember_old_values(
        instance,
        asset_fields=("featured_image_asset", "social_image_asset"),
    )


@receiver(post_save, sender=PostTranslation)
def cleanup_replaced_post_translation_assets(sender, instance, **kwargs):
    _cleanup_changed_assets(instance, ("featured_image_asset", "social_image_asset"))


@receiver(post_delete, sender=PostTranslation)
def cleanup_deleted_post_translation_assets(sender, instance, **kwargs):
    _cleanup_deleted_instance_media(
        instance,
        asset_fields=("featured_image_asset", "social_image_asset"),
    )
