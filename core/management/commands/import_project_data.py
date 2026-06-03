import time
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.db.utils import DatabaseError, IntegrityError, InterfaceError, OperationalError


class Command(BaseCommand):
    help = (
        "Import a JSON fixture object-by-object with lightweight retries. "
        "Useful for remote databases where a single loaddata transaction is fragile."
    )

    def add_arguments(self, parser):
        parser.add_argument("fixture", help="Path to the JSON fixture to import.")
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias to import into.",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Retries per object after OperationalError/InterfaceError.",
        )
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=1.0,
            help="Seconds to wait before retrying a failed object save.",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=10,
            help="Print progress every N imported objects.",
        )

    def handle(self, *args, **options):
        fixture_arg = options["fixture"]
        database = options["database"]
        retries = max(options["retries"], 1)
        retry_delay = max(options["retry_delay"], 0.0)
        progress_every = max(options["progress_every"], 1)

        fixture_path = Path(fixture_arg)
        if not fixture_path.is_absolute():
            fixture_path = Path(settings.BASE_DIR) / fixture_path
        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        imported = 0
        with fixture_path.open("r", encoding="utf-8") as fixture_file:
            pending = list(serializers.deserialize("json", fixture_file))

        pass_number = 0
        while pending:
            pass_number += 1
            imported_this_pass = 0
            next_pending = []

            self.stdout.write(
                f"Import pass {pass_number}: {len(pending)} pending objects"
            )

            for deserialized in pending:
                model_label = deserialized.object._meta.label
                pk = deserialized.object.pk
                attempt = 1

                while True:
                    try:
                        close_old_connections()
                        deserialized.save(using=database)
                        imported += 1
                        imported_this_pass += 1
                        if imported % progress_every == 0:
                            self.stdout.write(
                                f"Imported {imported} objects... last={model_label}(pk={pk})"
                            )
                        break
                    except (OperationalError, InterfaceError) as exc:
                        close_old_connections()
                        if attempt >= retries:
                            raise CommandError(
                                f"Failed importing {model_label}(pk={pk}) after {retries} attempts: {exc}"
                            ) from exc
                        self.stdout.write(
                            self.style.WARNING(
                                f"Retrying {model_label}(pk={pk}) after connection issue: {exc}"
                            )
                        )
                        attempt += 1
                        time.sleep(retry_delay)
                    except IntegrityError:
                        next_pending.append(deserialized)
                        break
                    except DatabaseError as exc:
                        raise CommandError(
                            f"Database error importing {model_label}(pk={pk}): {exc}"
                        ) from exc

            if not next_pending:
                break

            if imported_this_pass == 0:
                preview = ", ".join(
                    f"{obj.object._meta.label}(pk={obj.object.pk})"
                    for obj in next_pending[:10]
                )
                raise CommandError(
                    "No progress in import pass; unresolved foreign keys or data issues remain. "
                    f"Examples: {preview}"
                )

            pending = next_pending

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported} objects from {fixture_path}"
            )
        )
