import hashlib
import hmac
import json
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import (
    auto_reply_instagram_comments,
    draft_or_reply_instagram_messages,
    persist_instagram_messages,
    persist_instagram_payload,
)

logger = logging.getLogger(__name__)


def _meta_signature_error(request) -> str | None:
    if not settings.META_APP_SECRET:
        return None  # Solo desarrollo. En producción, configura META_APP_SECRET.
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return "missing_signature"
    expected = hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature.removeprefix("sha256="), expected):
        return "invalid_signature"
    return None


@csrf_exempt
def meta_instagram_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
            return HttpResponse(challenge or "", status=200)
        return HttpResponse("Verification failed", status=403)

    if request.method == "POST":
        signature_error = _meta_signature_error(request)
        if signature_error:
            logger.warning("Webhook de Meta rechazado: %s", signature_error)
            return JsonResponse({"ok": False, "error": signature_error}, status=403)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

        comments = persist_instagram_payload(payload)
        auto_replied = auto_reply_instagram_comments(comments)
        messages = persist_instagram_messages(payload)
        drafted_messages, sent_messages = draft_or_reply_instagram_messages(messages)
        return JsonResponse(
            {
                "ok": True,
                "stored_comments": len(comments),
                "auto_replied": auto_replied,
                "stored_messages": len(messages),
                "drafted_messages": drafted_messages,
                "sent_messages": sent_messages,
            }
        )

    return HttpResponse(status=405)
