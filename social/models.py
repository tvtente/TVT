from django.db import models
from fans.models import Fan

class Comment(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Recibido"
        DRAFTED = "drafted", "Borrador generado"
        APPROVED = "approved", "Aprobado"
        PUBLISHED = "published", "Publicado"
        IGNORED = "ignored", "Ignorado"
        ERROR = "error", "Error"

    platform = models.CharField(max_length=30, default="instagram")
    platform_comment_id = models.CharField(max_length=128, unique=True)
    media_id = models.CharField(max_length=128, blank=True)
    fan = models.ForeignKey(Fan, on_delete=models.PROTECT, related_name="comments")
    text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    platform_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.fan}: {self.text[:60]}"

class Response(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        APPROVED = "approved", "Aprobado"
        PUBLISHED = "published", "Publicado"
        REJECTED = "rejected", "Rechazado"

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="responses")
    text = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    risk_level = models.CharField(max_length=20, default="unknown")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    generated_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Respuesta a {self.comment_id} ({self.status})"


class DirectMessage(models.Model):
    """Mensaje privado entrante recibido por el webhook de Instagram."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Recibido"
        DRAFTED = "drafted", "Borrador generado"
        SENT = "sent", "Enviado"
        IGNORED = "ignored", "Ignorado"
        ERROR = "error", "Error"

    platform = models.CharField(max_length=30, default="instagram")
    platform_message_id = models.CharField(max_length=160, unique=True)
    fan = models.ForeignKey(Fan, on_delete=models.PROTECT, related_name="direct_messages")
    recipient_platform_id = models.CharField(max_length=128, blank=True)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    platform_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"DM de {self.fan}: {self.text[:60]}"


class MessageReply(models.Model):
    """Borrador o respuesta enviada para un mensaje privado."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Error de envío"

    message = models.ForeignKey(DirectMessage, on_delete=models.CASCADE, related_name="replies")
    text = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    risk_level = models.CharField(max_length=20, default="unknown")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    platform_message_id = models.CharField(max_length=160, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Respuesta privada a {self.message_id} ({self.status})"
