"""Persistencia y publicación de comentarios de Instagram."""

from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from ai_engine.service import ReplyGenerationError, generate_reply
from fans.models import Fan
from .models import Comment, DirectMessage, MessageReply, Response

logger = logging.getLogger(__name__)


class InstagramReplyError(Exception):
    """Error al publicar una respuesta en Instagram."""


def _extract_comment_events(payload: dict):
    """Extrae eventos de comentarios de payloads comunes de Instagram Webhooks.

    Meta puede variar campos según el producto/configuración. Conservamos raw_payload
    para poder ajustar el parser sin perder eventos reales.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") != "comments":
                continue

            from_user = value.get("from", {}) or {}
            comment_id = value.get("id") or value.get("comment_id")
            text = value.get("text", "")
            media = value.get("media", {}) or {}
            media_id = media.get("id", "")

            if comment_id:
                yield {
                    "comment_id": str(comment_id),
                    "text": text,
                    "media_id": str(media_id) if media_id else "",
                    "user_id": str(from_user.get("id") or from_user.get("username") or "unknown"),
                    "username": from_user.get("username", ""),
                    "display_name": from_user.get("name", ""),
                }


def persist_instagram_payload(payload: dict) -> list[Comment]:
    saved = []
    for event in _extract_comment_events(payload):
        fan, _ = Fan.objects.get_or_create(
            platform="instagram",
            platform_user_id=event["user_id"],
            defaults={
                "username": event["username"],
                "display_name": event["display_name"],
            },
        )
        dirty = False
        if event["username"] and fan.username != event["username"]:
            fan.username = event["username"]
            dirty = True
        if event["display_name"] and fan.display_name != event["display_name"]:
            fan.display_name = event["display_name"]
            dirty = True
        if dirty:
            fan.save(update_fields=["username", "display_name", "updated_at"])

        comment, created = Comment.objects.get_or_create(
            platform_comment_id=event["comment_id"],
            defaults={
                "platform": "instagram",
                "media_id": event["media_id"],
                "fan": fan,
                "text": event["text"],
                "raw_payload": payload,
            },
        )
        # Un webhook puede reenviarse. Solo los comentarios realmente nuevos
        # avanzan hacia la respuesta automática.
        if created:
            saved.append(comment)
    return saved


def _extract_message_events(payload: dict):
    """Extrae mensajes privados entrantes de los formatos de webhook de Meta.

    Se ignoran los ecos de mensajes que manda nuestra propia cuenta: no son una
    conversación nueva y responderlos crearía un bucle.
    """
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message") or {}
            if message.get("is_echo"):
                continue
            message_id = message.get("mid") or message.get("id")
            sender = (event.get("sender") or {}).get("id")
            recipient = (event.get("recipient") or {}).get("id")
            text = message.get("text") or ""
            if message_id and sender and text:
                yield {
                    "message_id": str(message_id),
                    "sender_id": str(sender),
                    "recipient_id": str(recipient or ""),
                    "text": text,
                }

        # Algunas configuraciones de Instagram entregan el mismo dato dentro
        # de changes[]. Admitimos ambos formatos para no perder mensajes.
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            message = value.get("message") or {}
            if message.get("is_echo"):
                continue
            message_id = message.get("mid") or message.get("id") or value.get("id")
            sender = (value.get("from") or value.get("sender") or {}).get("id")
            recipient = (value.get("to") or value.get("recipient") or {}).get("id")
            text = message.get("text") or value.get("text") or ""
            if message_id and sender and text:
                yield {
                    "message_id": str(message_id),
                    "sender_id": str(sender),
                    "recipient_id": str(recipient or ""),
                    "text": text,
                }


def persist_instagram_messages(payload: dict) -> list[DirectMessage]:
    """Guarda solo mensajes nuevos; Meta puede reenviar un mismo evento."""
    saved = []
    for event in _extract_message_events(payload):
        # Una entrega con el ID de nuestra cuenta no es un mensaje de cliente.
        if settings.INSTAGRAM_USER_ID and event["sender_id"] == settings.INSTAGRAM_USER_ID:
            continue
        fan, _ = Fan.objects.get_or_create(
            platform="instagram",
            platform_user_id=event["sender_id"],
        )
        message, created = DirectMessage.objects.get_or_create(
            platform_message_id=event["message_id"],
            defaults={
                "platform": "instagram",
                "fan": fan,
                "recipient_platform_id": event["recipient_id"],
                "text": event["text"],
                "raw_payload": payload,
            },
        )
        if created:
            saved.append(message)
    return saved


def auto_reply_instagram_comments(comments: list[Comment]) -> int:
    """Genera borradores y publica solo cuando el envío está activado.

    Los fallos se registran en base de datos pero nunca rompen el webhook: Meta
    debe recibir su 200 aunque Ollama o Instagram estén temporalmente caídos.
    """
    if not settings.INSTAGRAM_AUTO_DRAFT_COMMENTS_ENABLED:
        return 0

    processed = 0
    for comment in comments:
        if _is_our_own_comment(comment) or _risk_level_is_not_safe(comment):
            continue
        try:
            draft = generate_reply(comment=comment, fan=comment.fan)
            response = Response.objects.create(
                comment=comment,
                text=draft.text,
                model_name=draft.model_name,
                risk_level=draft.risk_level,
            )
            comment.status = Comment.Status.DRAFTED
            comment.save(update_fields=["status"])
            processed += 1

            if not settings.INSTAGRAM_AUTO_REPLY_ENABLED or _requires_human_review(comment.fan):
                continue

            publish_instagram_comment_reply(comment.platform_comment_id, draft.text)
        except (ReplyGenerationError, InstagramReplyError) as exc:
            comment.status = Comment.Status.ERROR
            comment.save(update_fields=["status"])
            logger.warning("No se pudo responder al comentario %s: %s", comment.id, exc)
            continue

        response.status = Response.Status.PUBLISHED
        response.save(update_fields=["status"])
        comment.status = Comment.Status.PUBLISHED
        comment.save(update_fields=["status"])
    return processed


def draft_or_reply_instagram_messages(messages: list[DirectMessage]) -> tuple[int, int]:
    """Crea borradores privados y, solo si se activa expresamente, los envía.

    El modo habitual de desarrollo usa solo borradores. Así se puede probar
    recepción y Gemma sin escribir a ninguna persona en Instagram.
    """
    if not settings.INSTAGRAM_AUTO_DRAFT_MESSAGES_ENABLED:
        return 0, 0

    drafted = sent = 0
    for message in messages:
        if _risk_level_is_not_safe(message):
            message.status = DirectMessage.Status.IGNORED
            message.save(update_fields=["status"])
            continue
        try:
            generated = generate_reply(comment=message, fan=message.fan)
            reply = MessageReply.objects.create(
                message=message,
                text=generated.text,
                model_name=generated.model_name,
                risk_level=generated.risk_level,
            )
            message.status = DirectMessage.Status.DRAFTED
            message.save(update_fields=["status"])
            drafted += 1

            if settings.INSTAGRAM_AUTO_REPLY_MESSAGES_ENABLED and not _requires_human_review(
                message.fan
            ):
                reply_id = publish_instagram_direct_message(
                    message.fan.platform_user_id, generated.text
                )
                reply.status = MessageReply.Status.SENT
                reply.platform_message_id = reply_id
                reply.save(update_fields=["status", "platform_message_id"])
                message.status = DirectMessage.Status.SENT
                message.save(update_fields=["status"])
                sent += 1
        except (ReplyGenerationError, InstagramReplyError) as exc:
            message.status = DirectMessage.Status.ERROR
            message.save(update_fields=["status"])
            logger.warning("No se pudo preparar respuesta al mensaje %s: %s", message.id, exc)
    return drafted, sent


def publish_instagram_comment_reply(comment_id: str, text: str) -> str:
    """Publica una respuesta pública bajo un comentario de Instagram."""
    if not settings.INSTAGRAM_USER_ACCESS_TOKEN:
        raise InstagramReplyError("Falta INSTAGRAM_USER_ACCESS_TOKEN en .env.")

    payload = json.dumps({"message": text}).encode("utf-8")
    request = Request(
        f"https://graph.instagram.com/{settings.INSTAGRAM_API_VERSION}/{comment_id}/replies",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.INSTAGRAM_USER_ACCESS_TOKEN}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise InstagramReplyError(f"Instagram respondió con error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise InstagramReplyError("No se pudo conectar con la API de Instagram.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstagramReplyError("Instagram devolvió una respuesta no válida.") from exc

    reply_id = data.get("id")
    if not reply_id:
        raise InstagramReplyError("Instagram no confirmó el identificador de la respuesta.")
    return str(reply_id)


def publish_instagram_direct_message(recipient_id: str, text: str) -> str:
    """Envía un texto privado a un usuario que ya inició la conversación."""
    if not settings.INSTAGRAM_USER_ACCESS_TOKEN or not settings.INSTAGRAM_USER_ID:
        raise InstagramReplyError(
            "Faltan INSTAGRAM_USER_ID o INSTAGRAM_USER_ACCESS_TOKEN en .env."
        )

    payload = json.dumps(
        {"recipient": {"id": recipient_id}, "message": {"text": text}}
    ).encode("utf-8")
    request = Request(
        f"https://graph.instagram.com/{settings.INSTAGRAM_API_VERSION}/"
        f"{settings.INSTAGRAM_USER_ID}/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.INSTAGRAM_USER_ACCESS_TOKEN}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise InstagramReplyError(f"Instagram respondió con error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise InstagramReplyError("No se pudo conectar con la API de Instagram.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstagramReplyError("Instagram devolvió una respuesta no válida.") from exc

    reply_id = data.get("message_id") or data.get("id")
    if not reply_id:
        raise InstagramReplyError("Instagram no confirmó el identificador del mensaje.")
    return str(reply_id)


def _is_our_own_comment(comment: Comment) -> bool:
    return bool(
        settings.INSTAGRAM_USER_ID
        and comment.fan.platform_user_id == settings.INSTAGRAM_USER_ID
    )


def _requires_human_review(fan: Fan) -> bool:
    """Una regla individual puede impedir el envío automático, no el borrador."""
    try:
        return fan.rule.human_review_required
    except ObjectDoesNotExist:
        return False


def _risk_level_is_not_safe(comment: Comment | DirectMessage) -> bool:
    """No automatizamos asuntos sensibles aunque la función esté activada."""
    from ai_engine.service import _risk_level

    return _risk_level(comment.text) != "low"
