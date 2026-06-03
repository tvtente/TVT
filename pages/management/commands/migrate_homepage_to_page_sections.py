from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from pages.models import HomeSection, Page, PageSection
from widgets.models import WidgetZone


MAIN_CONTENT_SECTION_TITLES = {
    "es": "Contenido principal heredado",
    "en": "Legacy main content",
    "ca": "Contingut principal heretat",
}


class Command(BaseCommand):
    help = "Copy the legacy homepage composition into PageSection rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-slug",
            help="Target page slug. Defaults to the current homepage page.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing PageSection rows on the target page before copying legacy sections.",
        )

    def handle(self, *args, **options):
        page = self._get_target_page(options.get("page_slug"))

        if page.page_sections.exists() and not options["replace"]:
            raise CommandError(
                "Target page already has PageSection rows. Use --replace to rebuild them."
            )

        with transaction.atomic():
            if options["replace"]:
                deleted_count, _details = page.page_sections.all().delete()
                self.stdout.write(f"Deleted existing page sections: {deleted_count}")

            created_sections = 0
            order = 0

            order, injected = self._copy_main_content_zone(page=page, start_order=order)
            created_sections += injected

            for legacy_section in HomeSection.objects.all().order_by("order", "id"):
                self._copy_home_section(
                    page=page,
                    home_section=legacy_section,
                    order=order,
                )
                order += 1
                created_sections += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Homepage migrated to PageSection successfully. Created sections: {created_sections}"
            )
        )

    def _get_target_page(self, page_slug):
        if page_slug:
            page = (
                Page.objects.filter(translations__slug=page_slug)
                .distinct()
                .first()
            )
            if page is None:
                raise CommandError(f"Page with slug '{page_slug}' was not found.")
            return page

        homepage = (
            Page.objects.filter(is_homepage=True)
            .order_by("-updated_at", "-created_at")
            .first()
        )
        if homepage is None:
            raise CommandError("No homepage page is configured.")
        return homepage

    def _copy_main_content_zone(self, *, page, start_order):
        zone = WidgetZone.objects.filter(slug="homepage-main-content").first()
        if zone is None or not zone.widgets.exists():
            return start_order, 0

        section = PageSection.objects.create(
            page=page,
            section_type=PageSection.SectionType.WIDGET_ZONE,
            widget_zone=zone,
            enabled=True,
            order=start_order,
            background_style=PageSection.BackgroundStyle.DEFAULT,
            full_width=False,
            show_separator_after=False,
        )
        for language_code, _label in settings.LANGUAGES:
            section.set_current_language(language_code)
            section.internal_title = MAIN_CONTENT_SECTION_TITLES.get(
                language_code,
                MAIN_CONTENT_SECTION_TITLES["en"],
            )
            section.save()

        self.stdout.write(
            f"Created PageSection for widget zone '{zone.slug}' at order {start_order}."
        )
        return start_order + 1, 1

    def _copy_home_section(self, *, page, home_section, order):
        section_type = PageSection.SectionType.CONTENT
        if home_section.widget_zone:
            if home_section.widget_zone.slug == "homepage-hero-right":
                section_type = PageSection.SectionType.HERO
            else:
                section_type = PageSection.SectionType.WIDGET_ZONE

        page_section = PageSection.objects.create(
            page=page,
            section_type=section_type,
            widget_zone=home_section.widget_zone,
            enabled=home_section.enabled,
            order=order,
            background_style=home_section.background_style,
            full_width=home_section.full_width,
            show_separator_after=home_section.show_separator_after,
        )

        for translation in home_section.translations.all():
            page_section.set_current_language(translation.language_code)
            page_section.internal_title = translation.title
            page_section.content = translation.content
            page_section.save()

        self.stdout.write(
            f"Copied HomeSection '{home_section.translated_title}' to PageSection order {order}."
        )
