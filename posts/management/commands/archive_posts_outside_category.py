from django.core.management.base import BaseCommand, CommandError

from categories.models import Category
from posts.models import Post


class Command(BaseCommand):
    help = "Archive posts that are not assigned to the selected category."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category-slug",
            default="fundamentos-de-la-prevencion-moderna",
            help="Slug of the category whose posts must remain unarchived.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the change. Without this flag the command only reports the count.",
        )

    def handle(self, *args, **options):
        category_slug = options["category_slug"]
        category = (
            Category.objects.filter(translations__slug=category_slug)
            .distinct()
            .first()
        )
        if category is None:
            raise CommandError(f"Category not found: {category_slug}")

        retained_categories = category.get_descendants(include_self=True)
        posts_to_archive = (
            Post.objects.exclude(categories__in=retained_categories)
            .exclude(status="archived")
            .distinct()
        )
        total = posts_to_archive.count()

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Would archive {total} post(s) outside category '{category_slug}'. "
                    "Run again with --apply to make the change."
                )
            )
            return

        posts_to_archive.update(status="archived")
        self.stdout.write(
            self.style.SUCCESS(
                f"Archived {total} post(s) outside category '{category_slug}'."
            )
        )
