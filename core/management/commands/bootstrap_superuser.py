from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the bootstrap superuser using environment variables."

    def handle(self, *args, **options):
        if not settings.BOOTSTRAP_SUPERUSER_ENABLED:
            raise CommandError(
                "BOOTSTRAP_SUPERUSER_ENABLED must be True to run this command."
            )

        password = settings.BOOTSTRAP_SUPERUSER_PASSWORD
        if not password:
            raise CommandError("BOOTSTRAP_SUPERUSER_PASSWORD is required.")

        username = settings.BOOTSTRAP_SUPERUSER_USERNAME
        email = settings.BOOTSTRAP_SUPERUSER_EMAIL

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser {username} {action}. Disable bootstrap after use."
            )
        )
