from django.test import TestCase
from django.utils.translation import override

from tags.models import Tag


class TagModelTests(TestCase):
    def test_get_slug_prefers_translated_slug_for_active_language(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = "english-slug"
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_slug(), "english-slug")

    def test_get_slug_falls_back_to_global_slug_when_translation_slug_is_missing(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = ""
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_slug(), "global-slug")

    def test_get_absolute_url_uses_active_language_slug(self):
        tag = Tag.objects.create(slug="global-slug")
        tag.set_current_language("en")
        tag.label = "Global label"
        tag.translated_slug = "english-slug"
        tag.save()

        with override("en"):
            self.assertEqual(tag.get_absolute_url(), "/en/posts/tag/english-slug/")
