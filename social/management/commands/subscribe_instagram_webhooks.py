"""Subscribe the configured Instagram professional account to webhook fields."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Suscribe la cuenta profesional de Instagram configurada a webhooks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fields",
            default="comments",
            help="Campos de webhook separados por comas (por defecto: comments).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Consulta las suscripciones actuales sin modificarlas.",
        )

    def handle(self, *args, **options):
        user_id = os.getenv("INSTAGRAM_USER_ID", "").strip()
        access_token = os.getenv("INSTAGRAM_USER_ACCESS_TOKEN", "").strip()
        api_version = os.getenv("INSTAGRAM_API_VERSION", "v26.0").strip()

        if not user_id or not access_token:
            raise CommandError(
                "Faltan INSTAGRAM_USER_ID o INSTAGRAM_USER_ACCESS_TOKEN en .env."
            )

        url = f"https://graph.instagram.com/{api_version}/{user_id}/subscribed_apps"
        if options["check"]:
            query = urlencode({"access_token": access_token})
            request = Request(f"{url}?{query}", method="GET")
            try:
                with urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                details = error.read().decode("utf-8", errors="replace")
                raise CommandError(
                    f"Meta rechazó la consulta (HTTP {error.code}): {details}"
                ) from error
            except URLError as error:
                raise CommandError(f"No se pudo conectar con Meta: {error.reason}") from error

            self.stdout.write("Suscripciones actuales: " + json.dumps(payload, ensure_ascii=False))
            return

        body = urlencode(
            {
                "subscribed_fields": options["fields"],
                "access_token": access_token,
            }
        ).encode("utf-8")
        request = Request(url, data=body, method="POST")

        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise CommandError(
                f"Meta rechazó la suscripción (HTTP {error.code}): {details}"
            ) from error
        except URLError as error:
            raise CommandError(f"No se pudo conectar con Meta: {error.reason}") from error

        if payload.get("success") is True:
            self.stdout.write(self.style.SUCCESS("Cuenta suscrita a: " + options["fields"]))
            return

        raise CommandError(f"Respuesta inesperada de Meta: {payload}")
