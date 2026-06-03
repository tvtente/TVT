from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


DEFAULT_OBJECT_LABELS = [
    "auth.user",
    "auth.group",
    "sites.site",
    "accounts",
    "books",
    "categories",
    "comments",
    "contact",
    "gallery",
    "menus",
    "pages",
    "posts",
    "publications",
    "shop",
    "site_settings",
    "tags",
    "testimonials",
    "widgets",
]

DEFAULT_EXCLUDES = [
    "admin",
    "auth.permission",
    "contenttypes",
    "sessions",
    "socialaccount",
]


class Command(BaseCommand):
    help = (
        "Export the project's useful local data to a JSON fixture so migrations "
        "can be reset without losing test content."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output",
            default="",
            help="Path to the output JSON fixture. Defaults to data_exports/project_backup_<timestamp>.json",
        )
        parser.add_argument(
            "--database",
            dest="database",
            default="default",
            help="Database alias to export from.",
        )
        parser.add_argument(
            "--without-shop",
            action="store_true",
            help="Exclude the shop app from the backup.",
        )

    def handle(self, *args, **options):
        output = options["output"]
        database = options["database"]
        include_shop = not options["without_shop"]

        export_dir = Path(settings.BASE_DIR) / "data_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output:
            output_path = Path(output)
            if not output_path.is_absolute():
                output_path = Path(settings.BASE_DIR) / output_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = export_dir / f"project_backup_{timestamp}.json"

        object_labels = list(DEFAULT_OBJECT_LABELS)
        if not include_shop and "shop" in object_labels:
            object_labels.remove("shop")

        excludes = list(DEFAULT_EXCLUDES)

        with output_path.open("w", encoding="utf-8") as fixture_file:
            call_command(
                "dumpdata",
                *object_labels,
                database=database,
                exclude=excludes,
                indent=2,
                stdout=fixture_file,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Project data backup created at {output_path}"
            )
        )
