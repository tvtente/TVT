from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export categories to a JSON fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "output",
            nargs="?",
            default="categories_export.json",
            help="Output JSON path.",
        )

    def handle(self, *args, **options):
        output = options["output"]
        with open(output, "w", encoding="utf-8") as fixture:
            call_command(
                "dumpdata",
                "categories.Category",
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                stdout=fixture,
            )

        self.stdout.write(self.style.SUCCESS(f"Categories exported to {output}"))
