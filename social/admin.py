from django.contrib import admin, messages

from ai_engine.service import ReplyGenerationError, generate_reply
from .models import Comment, DirectMessage, MessageReply, Response


@admin.action(description="Generar borrador con Tavata (no publica en Instagram)")
def generate_tavata_draft(modeladmin, request, queryset):
    """Genera respuestas de prueba desde el admin sin depender de Meta.

    Esta acción nunca usa las variables de envío automático ni llama a la API de
    Instagram. Cada ejecución queda guardada como Response para poder comparar
    respuestas de Tavata sobre el mismo comentario.
    """
    generated = errors = 0
    for comment in queryset.select_related("fan"):
        try:
            draft = generate_reply(comment=comment, fan=comment.fan)
        except ReplyGenerationError as exc:
            errors += 1
            modeladmin.message_user(
                request,
                f"Comentario #{comment.id}: {exc}",
                level=messages.ERROR,
            )
            continue

        Response.objects.create(
            comment=comment,
            text=draft.text,
            model_name=draft.model_name,
            risk_level=draft.risk_level,
        )
        comment.status = Comment.Status.DRAFTED
        comment.save(update_fields=["status"])
        generated += 1

    if generated:
        modeladmin.message_user(
            request,
            f"Tavata generó {generated} borrador(es). No se publicó nada en Instagram.",
            level=messages.SUCCESS,
        )
    if errors:
        modeladmin.message_user(
            request,
            f"No se pudieron generar {errors} borrador(es).",
            level=messages.WARNING,
        )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "fan", "platform", "status", "created_at")
    search_fields = ("text", "fan__username", "fan__display_name", "platform_comment_id")
    list_filter = ("platform", "status", "created_at")
    readonly_fields = ("raw_payload",)
    actions = (generate_tavata_draft,)

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "risk_level", "status", "generated_at")
    search_fields = ("text", "comment__fan__username")
    list_filter = ("risk_level", "status")


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "fan", "status", "created_at")
    search_fields = ("text", "fan__username", "fan__display_name", "platform_message_id")
    list_filter = ("platform", "status", "created_at")
    readonly_fields = ("raw_payload",)


@admin.register(MessageReply)
class MessageReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "risk_level", "status", "generated_at")
    search_fields = ("text", "message__fan__username")
    list_filter = ("risk_level", "status")
