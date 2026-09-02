from django.core.management.base import BaseCommand, CommandError
from parler.utils.context import switch_language

from widgets.models import Widget


class Command(BaseCommand):
    help = "Replace legacy PRL sidebar widgets with the dynamic Top Tags widget."

    def handle(self, *args, **options):
        legacy_widget = (
            Widget.objects.filter(translations__title__iexact="Bienestar mental")
            .prefetch_related("translations")
            .distinct()
            .first()
        )
        if legacy_widget is None:
            raise CommandError("Widget 'Bienestar mental' was not found.")

        removed_widgets = Widget.objects.filter(
            translations__title__iexact="Para reflexionar",
        ).distinct()
        removed_count = removed_widgets.count()

        legacy_widget.widget_type = Widget.WidgetType.POST_GRID_TOP_TAGS
        legacy_widget.top_tag_count = 3
        legacy_widget.save(update_fields=("widget_type", "top_tag_count"))

        for language_code, title in {
            "es": "Temas más consultados",
            "en": "Most consulted topics",
            "ca": "Temes més consultats",
        }.items():
            with switch_language(legacy_widget, language_code):
                legacy_widget.title = title
                legacy_widget.save()

        removed_widgets.delete()
        self.stdout.write(
            self.style.SUCCESS(
                "Converted 'Bienestar mental' to 'Temas más consultados' "
                f"and removed {removed_count} 'Para reflexionar' widget(s)."
            )
        )
