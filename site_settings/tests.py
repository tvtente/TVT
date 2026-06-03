from django.template import Context, Template
from django.test import TestCase

from site_settings.models import SiteConfiguration, SiteTemplate


class SiteConfigurationTests(TestCase):
    def test_get_solo_returns_singleton_instance(self):
        config = SiteConfiguration.get_solo()
        config.blog_items_per_page = 12
        config.save()

        same_config = SiteConfiguration.get_solo()

        self.assertEqual(config.pk, same_config.pk)
        self.assertEqual(same_config.blog_items_per_page, 12)
        self.assertEqual(str(same_config), "Site Configuration")


class SiteTemplateTests(TestCase):
    def test_save_keeps_only_one_template_chosen(self):
        first = SiteTemplate.objects.create(name="First", chosen=True)
        second = SiteTemplate.objects.create(name="Second", chosen=True)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.chosen)
        self.assertTrue(second.chosen)

    def test_get_chosen_creates_default_template_when_none_exists(self):
        chosen = SiteTemplate.get_chosen()

        self.assertTrue(chosen.chosen)
        self.assertEqual(chosen.name, "Default")

    def test_get_active_site_template_tag_returns_chosen_template(self):
        SiteTemplate.objects.create(name="Base", chosen=False)
        chosen = SiteTemplate.objects.create(name="Chosen", chosen=True)

        rendered = Template(
            "{% load settings_tags %}{% get_active_site_template as active %}{{ active.name }}"
        ).render(Context({}))

        self.assertEqual(rendered, chosen.name)
