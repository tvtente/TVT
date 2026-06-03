import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from gallery.asset_allocation import allocate_unique_asset_slug
from gallery.finalization import (
    FinalizationError,
    assign_direct_upload_slug,
    finalize_image_from_staging,
)
from gallery.language_inference import infer_gallery_image_language
from gallery.models import Image, StagedUpload
from gallery.utils import (
    register_gallery_image,
    sync_page_featured_image,
)
from pages.models import Page


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GalleryImageSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='editor',
            password='password',
        )

    def test_register_gallery_image_updates_title_and_description(self):
        upload = SimpleUploadedFile(
            'featured.jpg',
            b'fake-image',
            content_type='image/jpeg',
        )

        register_gallery_image(
            upload,
            'Original title',
            'Original summary',
        )
        image = register_gallery_image(
            upload,
            'Updated title',
            'Updated summary',
        )

        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(image.title, 'Updated title')
        self.assertEqual(image.description, 'Updated summary')
        self.assertTrue(image.slug)
        self.assertEqual(image.language, 'es')

    def test_sync_page_featured_image_is_noop_without_legacy_fields(self):
        page = Page.objects.create(
            author=self.user,
        )
        page.set_current_language("es")
        page.title = 'Pagina'
        page.slug = 'pagina'
        page.content = 'Contenido'
        page.meta_description = 'Resumen ES'
        page.save()

        page.set_current_language("en")
        page.title = 'Page EN'
        page.slug = 'page-en'
        page.content = 'Content'
        page.meta_description = 'Page summary EN'
        page.save()

        synced = sync_page_featured_image(page)

        self.assertEqual(synced, [])

    def test_sync_page_featured_image_ignores_existing_assets(self):
        gimg = Image(title='P', slug='p-asset', language='es', description='')
        gimg.image.save('p-asset.jpg', ContentFile(b'z'), save=True)

        page = Page.objects.create(
            author=self.user,
        )
        page.set_current_language("es")
        page.title = 'P'
        page.slug = 'p'
        page.content = 'c'
        page.featured_image_asset_es = gimg
        page.save()

        synced = sync_page_featured_image(page)
        self.assertEqual(synced, [])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GalleryPhase1MediaLibraryTests(TestCase):
    """Foundation: slug allocation, staging finalization metadata rules."""

    def test_allocate_unique_asset_slug_increments_when_slug_and_file_exist(self):
        img = Image(title='a', slug='hero', language='en', description='')
        img.image.save("hero.jpg", ContentFile(b"x"), save=True)

        slug, path = allocate_unique_asset_slug('hero', '.jpg')
        self.assertEqual(slug, 'hero-1')
        self.assertEqual(path, 'gallery/hero-1.jpg')

    def test_finalize_staged_rejects_missing_title(self):
        staged = StagedUpload.objects.create(
            file=SimpleUploadedFile('x.jpg', b'bytes', content_type='image/jpeg'),
        )
        instance = Image(title='', slug='tmp', language='en', description='')
        with self.assertRaises(FinalizationError):
            finalize_image_from_staging(
                instance=instance,
                staged=staged,
                slug_input='justice',
            )

    def test_finalize_staged_rejects_missing_language(self):
        staged = StagedUpload.objects.create(
            file=SimpleUploadedFile('x.jpg', b'y', content_type='image/jpeg'),
        )
        instance = Image(title='T', slug='tmp', language='', description='')
        with self.assertRaises(FinalizationError):
            finalize_image_from_staging(
                instance=instance,
                staged=staged,
                slug_input='justice',
            )

    def test_finalize_staged_allows_empty_description(self):
        staged = StagedUpload.objects.create(
            file=SimpleUploadedFile('x.jpg', b'abc', content_type='image/jpeg'),
        )
        instance = Image(title='T', slug='', language='es', description='')
        finalize_image_from_staging(
            instance=instance,
            staged=staged,
            slug_input='mi-imagen',
        )
        self.assertTrue(instance.slug)
        self.assertTrue(instance.image.name.startswith('gallery/'))
        self.assertEqual(instance.description, '')

    def test_assign_direct_upload_slug_rejects_non_slugifiable_input(self):
        obj = Image(title='t', slug='', language='en')
        with self.assertRaises(ValidationError):
            assign_direct_upload_slug(obj, slug_input='@@@', uploaded_name='a.jpg')

    def test_finalize_staged_rejects_invalid_slug(self):
        staged = StagedUpload.objects.create(
            file=SimpleUploadedFile('x.jpg', b'y', content_type='image/jpeg'),
        )
        instance = Image(title='T', slug='', language='en', description='')
        with self.assertRaises(FinalizationError):
            finalize_image_from_staging(
                instance=instance,
                staged=staged,
                slug_input='@@@',
            )


class GalleryLanguageInferenceTests(SimpleTestCase):
    def test_segment_justice_is_en(self):
        lang, reason = infer_gallery_image_language(slug="justice")
        self.assertEqual(lang, "en")
        self.assertEqual(reason, "keyword")

    def test_segment_justicia_is_es(self):
        lang, reason = infer_gallery_image_language(slug="justicia")
        self.assertEqual(lang, "es")
        self.assertEqual(reason, "keyword")

    def test_path_hint_en(self):
        lang, reason = infer_gallery_image_language(image_name="gallery/hero-en-banner.jpg")
        self.assertEqual(lang, "en")
        self.assertEqual(reason, "path_pattern")

    def test_no_signal_fallback_es(self):
        lang, reason = infer_gallery_image_language(title="xyz", slug="abc123", image_name="gallery/z9q.jpg")
        self.assertEqual(lang, "es")
        self.assertEqual(reason, "fallback_empty")

    def test_tie_fallback_es(self):
        lang, reason = infer_gallery_image_language(title="love amor mixed")
        self.assertEqual(lang, "es")
        self.assertEqual(reason, "fallback_tie")

    def test_spanish_punctuation_boost(self):
        lang, reason = infer_gallery_image_language(title="¿Quién es?")
        self.assertEqual(lang, "es")
        self.assertEqual(reason, "keyword")

    def test_catalan_keyword(self):
        lang, reason = infer_gallery_image_language(title="Informació general")
        self.assertEqual(lang, "ca")
        self.assertEqual(reason, "keyword")
