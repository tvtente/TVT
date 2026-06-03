from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pages.models import Page, PageSection


DEFAULT_TRANSLATIONS = {
    "en": {
        "internal_title": "Embedded homepage page",
        "heading": "",
        "content": "",
        "button_text": "",
        "button_url": "",
    },
    "es": {
        "internal_title": "Pagina incrustada en inicio",
        "heading": "",
        "content": "",
        "button_text": "",
        "button_url": "",
    },
    "ca": {
        "internal_title": "Pagina incrustada a inici",
        "heading": "",
        "content": "",
        "button_text": "",
        "button_url": "",
    },
}


class Command(BaseCommand):
    help = "Insert an embedded-page PageSection into the modular homepage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--linked-page-slug",
            required=True,
            help="Slug of the page that should be embedded into the homepage.",
        )
        parser.add_argument(
            "--page-slug",
            help="Target homepage slug. Defaults to the current homepage page.",
        )
        parser.add_argument(
            "--order",
            type=int,
            help="Optional explicit order for the inserted section.",
        )
        parser.add_argument(
            "--heading-en",
            default="",
            help="Optional English heading override for the embedded section.",
        )
        parser.add_argument(
            "--heading-es",
            default="",
            help="Optional Spanish heading override for the embedded section.",
        )
        parser.add_argument(
            "--heading-ca",
            default="",
            help="Optional Catalan heading override for the embedded section.",
        )

    def handle(self, *args, **options):
        homepage = self._get_target_page(options.get("page_slug"))
        linked_page = self._get_linked_page(options["linked_page_slug"])

        if homepage.pk == linked_page.pk:
            raise CommandError("The homepage cannot embed itself.")

        with transaction.atomic():
            section = (
                homepage.page_sections.filter(
                    section_type=PageSection.SectionType.PAGE,
                    linked_page=linked_page,
                )
                .order_by("id")
                .first()
            )

            created = section is None
            if created:
                section = PageSection.objects.create(
                    page=homepage,
                    section_type=PageSection.SectionType.PAGE,
                    linked_page=linked_page,
                    enabled=True,
                    order=self._resolve_order(homepage, options.get("order")),
                    background_style=PageSection.BackgroundStyle.DEFAULT,
                    full_width=False,
                    show_separator_after=False,
                )
            else:
                if options.get("order") is not None:
                    section.order = options["order"]
                section.enabled = True
                section.linked_page = linked_page
                section.section_type = PageSection.SectionType.PAGE
                section.save()

            for language_code, _label in settings.LANGUAGES:
                translation = DEFAULT_TRANSLATIONS.get(
                    language_code,
                    DEFAULT_TRANSLATIONS["en"],
                ).copy()
                heading_override = options.get(f"heading_{language_code}", "").strip()
                if heading_override:
                    translation["heading"] = heading_override

                section.set_current_language(language_code)
                section.internal_title = translation["internal_title"]
                section.heading = translation["heading"]
                section.content = translation["content"]
                section.button_text = translation["button_text"]
                section.button_url = translation["button_url"]
                section.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} embedded-page section for '{linked_page.translated_title}' in homepage '{homepage.translated_title}'."
            )
        )

    def _get_target_page(self, page_slug):
        if page_slug:
            page = Page.objects.filter(translations__slug=page_slug).distinct().first()
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

    def _get_linked_page(self, page_slug):
        page = Page.objects.filter(translations__slug=page_slug).distinct().first()
        if page is None:
            raise CommandError(f"Linked page with slug '{page_slug}' was not found.")
        return page

    def _resolve_order(self, homepage, explicit_order):
        if explicit_order is not None:
            return explicit_order
        max_order = (
            homepage.page_sections.order_by("-order")
            .values_list("order", flat=True)
            .first()
        )
        if max_order is None:
            return 1
        return max_order + 1
