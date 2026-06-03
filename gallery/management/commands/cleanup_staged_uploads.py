from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from gallery.models import StagedUpload


class Command(BaseCommand):
    help = "Remove expired gallery staged uploads (temporary files under gallery/_staging/)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ttl-hours",
            type=int,
            default=72,
            help="Delete staged rows older than this many hours (default: 72).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many rows would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        ttl = options["ttl_hours"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=ttl)
        qs = StagedUpload.objects.filter(created_at__lt=cutoff)
        ids = list(qs.values_list("pk", flat=True))
        if dry_run:
            self.stdout.write(
                f"Would delete {len(ids)} staged upload(s) older than {ttl}h (cutoff {cutoff}).",
            )
            return
        removed = 0
        for staged in StagedUpload.objects.filter(pk__in=ids).iterator(chunk_size=100):
            staged.delete()
            removed += 1
        self.stdout.write(self.style.SUCCESS(f"Deleted {removed} staged upload(s) and their files."))
