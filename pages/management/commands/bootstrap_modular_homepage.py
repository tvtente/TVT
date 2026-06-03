from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pages.models import Page, PageSection
from widgets.models import Widget, WidgetZone


ZONE_DEFINITIONS = (
    {
        "slug": "homepage-hero",
        "name": {
            "en": "Homepage Hero",
            "es": "Hero de inicio",
            "ca": "Hero d'inici",
        },
        "widget_type": Widget.WidgetType.HERO_CAROUSEL,
        "widget_order": 1,
        "widget_defaults": {
            "item_count": 3,
            "cache_timeout": 900,
            "column_count": 1,
            "carousel_interval_ms": 5500,
            "view_all_link_url": "/posts/",
        },
        "widget_translations": {
            "en": {
                "title": "Homepage hero",
                "section_title": "Featured debates",
                "view_all_link_text": "Explore all articles",
            },
            "es": {
                "title": "Hero de inicio",
                "section_title": "Debates destacados",
                "view_all_link_text": "Explorar todos los articulos",
            },
            "ca": {
                "title": "Hero d'inici",
                "section_title": "Debats destacats",
                "view_all_link_text": "Explorar tots els articles",
            },
        },
        "section_type": PageSection.SectionType.HERO,
        "section_defaults": {
            "background_style": PageSection.BackgroundStyle.DEFAULT,
            "full_width": False,
            "show_separator_after": False,
        },
        "section_translations": {
            "en": {
                "internal_title": "Homepage hero section",
                "heading": "Think with TVTente",
                "content": "<p>Critical reflection, highlighted debates, and editorially curated ideas for the homepage.</p>",
                "button_text": "Explore articles",
                "button_url": "/posts/",
            },
            "es": {
                "internal_title": "Seccion hero de inicio",
                "heading": "Pensar con TVTente",
                "content": "<p>Reflexion critica, debates destacados e ideas seleccionadas editorialmente para la portada.</p>",
                "button_text": "Explorar articulos",
                "button_url": "/posts/",
            },
            "ca": {
                "internal_title": "Seccio hero d'inici",
                "heading": "Pensar amb TVTente",
                "content": "<p>Reflexio critica, debats destacats i idees seleccionades editorialment per a la portada.</p>",
                "button_text": "Explorar articles",
                "button_url": "/posts/",
            },
        },
    },
    {
        "slug": "homepage-books",
        "name": {
            "en": "Homepage Books",
            "es": "Libros de inicio",
            "ca": "Llibres d'inici",
        },
        "widget_type": Widget.WidgetType.BOOK_GRID_RECENT,
        "widget_order": 1,
        "widget_defaults": {
            "item_count": 6,
            "cache_timeout": 1800,
            "column_count": 3,
            "view_all_link_url": "/books/",
        },
        "widget_translations": {
            "en": {
                "title": "Homepage books",
                "section_title": "Recent books",
                "view_all_link_text": "See all books",
            },
            "es": {
                "title": "Libros de inicio",
                "section_title": "Libros recientes",
                "view_all_link_text": "Ver todos los libros",
            },
            "ca": {
                "title": "Llibres d'inici",
                "section_title": "Llibres recents",
                "view_all_link_text": "Veure tots els llibres",
            },
        },
        "section_type": PageSection.SectionType.WIDGET_ZONE,
        "section_defaults": {
            "background_style": PageSection.BackgroundStyle.SURFACE,
            "full_width": False,
            "show_separator_after": True,
        },
        "section_translations": {
            "en": {
                "internal_title": "Homepage books section",
                "heading": "Books and editorial work",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
            "es": {
                "internal_title": "Seccion de libros de inicio",
                "heading": "Libros y trabajo editorial",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
            "ca": {
                "internal_title": "Seccio de llibres d'inici",
                "heading": "Llibres i treball editorial",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
        },
    },
    {
        "slug": "homepage-publications",
        "name": {
            "en": "Homepage Publications",
            "es": "Publicaciones de inicio",
            "ca": "Publicacions d'inici",
        },
        "widget_type": Widget.WidgetType.PUBLICATION_GRID_RECENT,
        "widget_order": 1,
        "widget_defaults": {
            "item_count": 6,
            "cache_timeout": 1800,
            "column_count": 3,
            "view_all_link_url": "/publications/",
        },
        "widget_translations": {
            "en": {
                "title": "Homepage publications",
                "section_title": "Recent publications",
                "view_all_link_text": "See all publications",
            },
            "es": {
                "title": "Publicaciones de inicio",
                "section_title": "Publicaciones recientes",
                "view_all_link_text": "Ver todas las publicaciones",
            },
            "ca": {
                "title": "Publicacions d'inici",
                "section_title": "Publicacions recents",
                "view_all_link_text": "Veure totes les publicacions",
            },
        },
        "section_type": PageSection.SectionType.WIDGET_ZONE,
        "section_defaults": {
            "background_style": PageSection.BackgroundStyle.DEFAULT,
            "full_width": False,
            "show_separator_after": False,
        },
        "section_translations": {
            "en": {
                "internal_title": "Homepage publications section",
                "heading": "Research and publications",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
            "es": {
                "internal_title": "Seccion de publicaciones de inicio",
                "heading": "Investigacion y publicaciones",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
            "ca": {
                "internal_title": "Seccio de publicacions d'inici",
                "heading": "Recerca i publicacions",
                "content": "",
                "button_text": "",
                "button_url": "",
            },
        },
    },
)


class Command(BaseCommand):
    help = "Create or update a modular homepage scaffold with hero, books, and publications widgets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-slug",
            help="Target page slug. Defaults to the current homepage page.",
        )
        parser.add_argument(
            "--replace-sections",
            action="store_true",
            help="Delete existing PageSection rows on the target page before creating the scaffold.",
        )
        parser.add_argument(
            "--replace-widgets",
            action="store_true",
            help="Delete widgets in the scaffold zones before recreating the default ones.",
        )

    def handle(self, *args, **options):
        page = self._get_target_page(options.get("page_slug"))

        with transaction.atomic():
            if options["replace_sections"]:
                deleted_count, _details = page.page_sections.all().delete()
                self.stdout.write(f"Deleted existing page sections: {deleted_count}")

            for definition in ZONE_DEFINITIONS:
                zone = self._ensure_zone(definition)
                widget = self._ensure_widget(zone, definition, replace=options["replace_widgets"])
                section = self._ensure_section(page, zone, definition)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Prepared zone '{zone.slug}', widget '{widget.widget_type}', section '{section.translated_internal_title}'."
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

    def _ensure_zone(self, definition):
        zone, _created = WidgetZone.objects.get_or_create(
            slug=definition["slug"],
            defaults={"name": definition["name"]["en"]},
        )
        zone.name = definition["name"]["en"]
        zone.save(update_fields=["name"])
        return zone

    def _ensure_widget(self, zone, definition, *, replace):
        widgets = Widget.objects.filter(zone=zone)
        if replace:
            widgets.delete()
            widget = None
        else:
            widget = widgets.filter(widget_type=definition["widget_type"]).order_by("id").first()

        if widget is None:
            widget = Widget.objects.create(
                zone=zone,
                widget_type=definition["widget_type"],
                order=definition["widget_order"],
                **definition["widget_defaults"],
            )
        else:
            widget.widget_type = definition["widget_type"]
            widget.order = definition["widget_order"]
            for field_name, value in definition["widget_defaults"].items():
                setattr(widget, field_name, value)
            widget.save()

        for language_code, _label in settings.LANGUAGES:
            translation = definition["widget_translations"].get(
                language_code,
                definition["widget_translations"]["en"],
            )
            widget.set_current_language(language_code)
            widget.title = translation["title"]
            widget.section_title = translation["section_title"]
            widget.view_all_link_text = translation["view_all_link_text"]
            widget.save()

        return widget

    def _ensure_section(self, page, zone, definition):
        section = (
            page.page_sections.filter(widget_zone=zone)
            .order_by("id")
            .first()
        )
        if section is None:
            order = self._next_section_order(page)
            section = PageSection.objects.create(
                page=page,
                widget_zone=zone,
                order=order,
                enabled=True,
                section_type=definition["section_type"],
                **definition["section_defaults"],
            )
        else:
            section.enabled = True
            section.section_type = definition["section_type"]
            for field_name, value in definition["section_defaults"].items():
                setattr(section, field_name, value)
            section.save()

        for language_code, _label in settings.LANGUAGES:
            translation = definition["section_translations"].get(
                language_code,
                definition["section_translations"]["en"],
            )
            section.set_current_language(language_code)
            section.internal_title = translation["internal_title"]
            section.heading = translation["heading"]
            section.content = translation["content"]
            section.button_text = translation["button_text"]
            section.button_url = translation["button_url"]
            section.save()

        return section

    def _next_section_order(self, page):
        max_order = page.page_sections.order_by("-order").values_list("order", flat=True).first()
        if max_order is None:
            return 1
        return max_order + 1
