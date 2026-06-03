from django.core.management.base import BaseCommand

from gallery.utils import sync_all_content_images


class Command(BaseCommand):
    help = "Registers Post/Page featured images in Gallery Image."

    def handle(self, *args, **options):
        synced_images = sync_all_content_images()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {len(synced_images)} content images into Gallery Image."
            )
        )
