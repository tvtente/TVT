from django.contrib import admin
from .models import Comment, DirectMessage, MessageReply, Response

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "fan", "platform", "status", "created_at")
    search_fields = ("text", "fan__username", "fan__display_name", "platform_comment_id")
    list_filter = ("platform", "status", "created_at")
    readonly_fields = ("raw_payload",)

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
