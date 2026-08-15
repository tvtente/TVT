"""Crea una entrega de webhook local para probar mensajes privados sin Meta."""

from django.core.management.base import BaseCommand, CommandError

from social.services import draft_or_reply_instagram_messages, persist_instagram_messages


class Command(BaseCommand):
    help = "Simula un mensaje directo de Instagram y crea un borrador con Ollama."

    def add_arguments(self, parser):
        parser.add_argument("--text", required=True, help="Texto del mensaje de prueba.")
        parser.add_argument(
            "--sender-id", default="local-demo-user", help="IGSID ficticio para la prueba."
        )
        parser.add_argument(
            "--message-id", default="", help="ID único opcional para repetir pruebas."
        )

    def handle(self, *args, **options):
        text = options["text"].strip()
        if not text:
            raise CommandError("--text no puede estar vacío.")

        from uuid import uuid4

        message_id = options["message_id"] or f"local-{uuid4()}"
        payload = {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": options["sender_id"]},
                            "recipient": {"id": "local-instagram-account"},
                            "message": {"mid": message_id, "text": text},
                        }
                    ]
                }
            ]
        }
        messages = persist_instagram_messages(payload)
        drafted, sent = draft_or_reply_instagram_messages(messages)
        if not messages:
            self.stdout.write(self.style.WARNING("No se creó mensaje: ID ya usado o emisor propio."))
            return
        message = messages[0]
        self.stdout.write(self.style.SUCCESS(f"Mensaje #{message.id} guardado: {message.status}"))
        self.stdout.write(f"Borradores: {drafted}; enviados a Instagram: {sent}")
        if message.replies.exists():
            self.stdout.write(f"Respuesta de Gemma: {message.replies.first().text}")
