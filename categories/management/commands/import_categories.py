from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from categories.models import Category


class Command(BaseCommand):
    help = "Import categories from a JSON fixture, backing up current data first."

    def add_arguments(self, parser):
        parser.add_argument(
            "input",
            nargs="?",
            default="categories_export.json",
            help="Input JSON fixture path.",
        )
        parser.add_argument(
            "--backup",
            default="categories_backup_before_import.json",
            help="Backup JSON path created before import.",
        )

    def handle(self, *args, **options):
        input_path = options["input"]
        backup_path = options["backup"]

        try:
            with open(input_path, "r", encoding="utf-8"):
                pass
        except FileNotFoundError as exc:
            raise CommandError(f"Input fixture not found: {input_path}") from exc

        self.stdout.write(f"Creating backup at {backup_path}")
        with open(backup_path, "w", encoding="utf-8") as backup:
            call_command(
                "dumpdata",
                "categories.Category",
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                stdout=backup,
            )

        self.stdout.write(f"Importing categories from {input_path}")
        call_command("loaddata", input_path)

        self.stdout.write("Rebuilding category tree")
        Category.objects.rebuild()

        self.stdout.write(self.style.SUCCESS("Categories import completed"))
