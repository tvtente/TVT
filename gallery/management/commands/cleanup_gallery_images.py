from django.core.management.base import BaseCommand

from gallery.models import Image


class Command(BaseCommand):
    help = "Remove gallery.Image rows that have no stored image file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many gallery rows would be deleted without deleting them.",
        )
        parser.add_argument(
            "--missing-files",
            action="store_true",
            help="Also delete rows whose image path is set in the DB but the file is missing from storage.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        include_missing_files = options["missing_files"]

        empty_qs = Image.objects.filter(image__isnull=True) | Image.objects.filter(image="")
        ids_to_delete = set(empty_qs.values_list("pk", flat=True))

        missing_file_ids = []
        if include_missing_files:
            for image in Image.objects.exclude(image__isnull=True).exclude(image="").iterator(chunk_size=200):
                image_name = getattr(image.image, "name", "") or ""
                if image_name and not image.image.storage.exists(image_name):
                    missing_file_ids.append(image.pk)
            ids_to_delete.update(missing_file_ids)

        total = len(ids_to_delete)

        if dry_run:
            self.stdout.write(
                f"Would delete {total} gallery image row(s) without a usable image file.",
            )
            if include_missing_files:
                self.stdout.write(
                    f"Rows with DB file path but missing storage file: {len(missing_file_ids)}.",
                )
            return

        removed = 0
        for image in Image.objects.filter(pk__in=ids_to_delete).iterator(chunk_size=200):
            image.delete()
            removed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {removed} gallery image row(s) without a usable image file."
            )
        )
