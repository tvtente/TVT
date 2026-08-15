import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from ai_engine.service import GeneratedReply
from fans.models import Fan
from social.models import Comment, DirectMessage, MessageReply, Response
from social.services import auto_reply_instagram_comments


def sample_payload():
    return {
        "entry": [
            {
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment-demo-001",
                            "text": "Qué hermosa Tavata",
                            "from": {
                                "id": "fan-demo-1",
                                "username": "demo_fan",
                                "name": "Demo Fan",
                            },
                            "media": {"id": "media-demo-1"},
                        },
                    }
                ]
            }
        ]
    }


def sample_message_payload():
    return {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "igsid-demo-1"},
                        "recipient": {"id": "our-account"},
                        "message": {
                            "mid": "message-demo-001",
                            "text": "Hola, ¿me puedes ayudar?",
                        },
                    }
                ]
            }
        ]
    }


@override_settings(INSTAGRAM_AUTO_REPLY_ENABLED=False)
class MetaInstagramWebhookTests(TestCase):
    def setUp(self):
        self.url = reverse("meta-instagram-webhook")

    @override_settings(META_VERIFY_TOKEN="test-token")
    def test_accepts_meta_verification(self):
        response = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "challenge-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"challenge-123")

    @override_settings(META_VERIFY_TOKEN="test-token")
    def test_rejects_invalid_verification_token(self):
        response = self.client.get(
            self.url,
            {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(META_APP_SECRET="")
    def test_persists_comment_and_fan_once(self):
        body = json.dumps(sample_payload())

        response = self.client.post(self.url, data=body, content_type="application/json")
        duplicate_response = self.client.post(self.url, data=body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "stored_comments": 1,
                "auto_replied": 0,
                "stored_messages": 0,
                "drafted_messages": 0,
                "sent_messages": 0,
            },
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Fan.objects.count(), 1)

        comment = Comment.objects.get()
        self.assertEqual(comment.text, "Qué hermosa Tavata")
        self.assertEqual(comment.fan.username, "demo_fan")
        self.assertEqual(comment.media_id, "media-demo-1")

    @override_settings(META_APP_SECRET="app-secret")
    def test_requires_valid_signature_when_app_secret_is_configured(self):
        body = json.dumps(sample_payload()).encode("utf-8")
        signature = hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()

        rejected = self.client.post(self.url, data=body, content_type="application/json")
        accepted = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": f"sha256={signature}"},
        )

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)

    @override_settings(META_APP_SECRET="", INSTAGRAM_USER_ID="our-account")
    def test_persists_direct_message_once(self):
        body = json.dumps(sample_message_payload())
        response = self.client.post(self.url, data=body, content_type="application/json")
        duplicate = self.client.post(self.url, data=body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stored_messages"], 1)
        self.assertEqual(duplicate.json()["stored_messages"], 0)
        message = DirectMessage.objects.get()
        self.assertEqual(message.text, "Hola, ¿me puedes ayudar?")
        self.assertEqual(message.fan.platform_user_id, "igsid-demo-1")


@override_settings(
    INSTAGRAM_AUTO_REPLY_ENABLED=True,
    INSTAGRAM_AUTO_DRAFT_COMMENTS_ENABLED=True,
    INSTAGRAM_USER_ID="our-account",
)
class AutoReplyTests(TestCase):
    def setUp(self):
        fan = Fan.objects.create(platform_user_id="fan-1", username="fan")
        self.comment = Comment.objects.create(
            platform_comment_id="comment-1", fan=fan, text="Qué bonita Tavata"
        )

    @patch("social.services.publish_instagram_comment_reply", return_value="reply-1")
    @patch("social.services.generate_reply")
    def test_publishes_low_risk_draft_for_a_new_comment(self, mock_generate, mock_publish):
        mock_generate.return_value = GeneratedReply(
            text="¡Muchas gracias por tu cariño! 😊",
            model_name="gemma3:4b",
            risk_level="low",
        )

        published = auto_reply_instagram_comments([self.comment])

        self.assertEqual(published, 1)
        mock_publish.assert_called_once_with(
            "comment-1", "¡Muchas gracias por tu cariño! 😊"
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, Comment.Status.PUBLISHED)
        self.assertEqual(Response.objects.get().status, Response.Status.PUBLISHED)

    @patch("social.services.publish_instagram_comment_reply")
    @patch("social.services.generate_reply")
    def test_does_not_auto_reply_to_high_risk_comment(self, mock_generate, mock_publish):
        self.comment.text = "Necesito consejo médico"
        self.comment.save(update_fields=["text"])

        published = auto_reply_instagram_comments([self.comment])

        self.assertEqual(published, 0)
        mock_generate.assert_not_called()
        mock_publish.assert_not_called()


@override_settings(
    INSTAGRAM_AUTO_DRAFT_MESSAGES_ENABLED=True,
    INSTAGRAM_AUTO_REPLY_MESSAGES_ENABLED=False,
    INSTAGRAM_USER_ID="our-account",
)
class DirectMessageDraftTests(TestCase):
    @patch("social.services.generate_reply")
    def test_creates_a_draft_without_sending_to_instagram(self, mock_generate):
        mock_generate.return_value = GeneratedReply(
            text="¡Hola! Claro, cuéntame cómo podemos ayudarte.",
            model_name="gemma3:4b",
            risk_level="low",
        )
        response = self.client.post(
            reverse("meta-instagram-webhook"),
            data=json.dumps(sample_message_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["drafted_messages"], 1)
        self.assertEqual(response.json()["sent_messages"], 0)
        self.assertEqual(MessageReply.objects.count(), 1)
        self.assertEqual(MessageReply.objects.get().status, MessageReply.Status.DRAFT)
