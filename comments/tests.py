from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.translation import override
from unittest.mock import Mock, patch

from comments.models import Comment, CommentTranslation
from posts.models import Post


User = get_user_model()


@override_settings(LANGUAGES=(("es", "Español"), ("en", "English"), ("ca", "Català")))
class CommentLanguageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="commenter",
            email="commenter@example.com",
            password="test-pass-123",
        )
        self.staff_user = User.objects.create_user(
            username="moderator",
            email="moderator@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.post = Post.objects.create(
            author=self.user,
            status="published",
        )
        self.post.set_current_language("es")
        self.post.title = "Articulo de prueba"
        self.post.slug = "articulo-prueba"
        self.post.content = "Contenido en español"
        self.post.save()

        self.post.set_current_language("en")
        self.post.title = "Test article"
        self.post.slug = "test-article"
        self.post.content = "Content in English"
        self.post.save()

    def test_new_comment_saves_current_language(self):
        self.client.force_login(self.user)

        with override("es"):
            response = self.client.post(
                self.post.get_absolute_url_for_language("es"),
                {
                    "content": "Comentario original en español",
                    "parent": "",
                },
            )

        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get(post=self.post)
        self.assertEqual(comment.language, "es")
        self.assertEqual(comment.content, "Comentario original en español")

    def test_post_detail_shows_original_comment_language_badge(self):
        Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )

        with override("en"):
            response = self.client.get(self.post.get_absolute_url_for_language("en"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comment in Español")
        self.assertContains(response, "Translate")
        self.assertContains(response, "Comentario original en español")

    def test_comment_translation_is_used_for_preferred_language(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        CommentTranslation.objects.create(
            comment=comment,
            language="en",
            content="Original comment translated to English",
            source=CommentTranslation.Source.HUMAN,
            translated_by=self.user,
        )

        with override("en"):
            response = self.client.get(self.post.get_absolute_url_for_language("en"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comment in Español")
        self.assertContains(response, "View original")
        self.assertContains(response, "View translation")
        self.assertContains(response, "Community translation")
        self.assertContains(response, "Translated by commenter")
        self.assertContains(response, "Original")
        self.assertContains(response, "Original comment translated to English")
        self.assertContains(response, "Comentario original en español")

    def test_legacy_single_translation_fields_still_work_as_fallback(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            translated_content="Legacy translation in English",
            translation_language="en",
            is_approved=True,
        )

        with override("en"):
            rendered = comment.get_display_content()

        self.assertEqual(rendered, "Legacy translation in English")

    def test_translate_endpoint_returns_cached_translation(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        CommentTranslation.objects.create(
            comment=comment,
            language="en",
            content="Cached translation in English",
            source=CommentTranslation.Source.HUMAN,
            translated_by=self.user,
        )

        with override("en"):
            response = self.client.get(
                reverse("comments:translate_comment", kwargs={"comment_id": comment.id}),
                {"language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["content"], "Cached translation in English")
        self.assertTrue(payload["cached"])

    @override_settings(COMMENT_TRANSLATION_PROVIDER="mock")
    def test_translate_endpoint_generates_translation_on_demand(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )

        with override("en"):
            response = self.client.get(
                reverse("comments:translate_comment", kwargs={"comment_id": comment.id}),
                {"language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["content"], "[en] Comentario original en español")
        self.assertFalse(payload["cached"])
        self.assertTrue(
            CommentTranslation.objects.filter(
                comment=comment,
                language="en",
                provider="mock",
            ).exists()
        )

    @override_settings(COMMENT_TRANSLATION_PROVIDER="disabled")
    def test_translate_endpoint_returns_controlled_error_when_provider_disabled(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )

        with override("en"):
            response = self.client.get(
                reverse("comments:translate_comment", kwargs={"comment_id": comment.id}),
                {"language": "en"},
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("Automatic translation", payload["error"])

    @override_settings(
        COMMENT_TRANSLATION_PROVIDER="deepl",
        DEEPL_API_KEY="test-deepl-key",
        DEEPL_API_URL="https://api-free.deepl.com/v2/translate",
        COMMENT_TRANSLATION_TIMEOUT=7,
    )
    @patch("comments.services.requests.post")
    def test_translate_endpoint_uses_deepl_provider(self, mocked_post):
        mocked_response = Mock()
        mocked_response.json.return_value = {
            "translations": [
                {
                    "text": "Original comment translated with DeepL",
                }
            ]
        }
        mocked_response.raise_for_status.return_value = None
        mocked_post.return_value = mocked_response

        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )

        with override("en"):
            response = self.client.get(
                reverse("comments:translate_comment", kwargs={"comment_id": comment.id}),
                {"language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["content"], "Original comment translated with DeepL")
        self.assertEqual(payload["provider"], "deepl")
        self.assertFalse(payload["cached"])

        mocked_post.assert_called_once()
        _, kwargs = mocked_post.call_args
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "DeepL-Auth-Key test-deepl-key",
        )
        self.assertEqual(kwargs["json"]["target_lang"], "EN")
        self.assertEqual(kwargs["json"]["source_lang"], "ES")

    @override_settings(
        COMMENT_TRANSLATION_PROVIDER="deepl",
        DEEPL_API_KEY="",
    )
    def test_translate_endpoint_returns_controlled_error_when_deepl_key_missing(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )

        with override("en"):
            response = self.client.get(
                reverse("comments:translate_comment", kwargs={"comment_id": comment.id}),
                {"language": "en"},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("DEEPL_API_KEY", payload["error"])

    def test_authenticated_user_translation_suggestion_is_queued_for_review(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        self.client.force_login(self.user)

        with override("en"):
            response = self.client.post(
                reverse("comments:suggest_comment_translation", kwargs={"comment_id": comment.id}),
                {
                    "language": "en",
                    "content": "Community translation in English",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["pending_review"])
        self.assertIn("awaiting moderation", payload["message"])
        translation = CommentTranslation.objects.get(comment=comment, language="en")
        self.assertEqual(translation.content, "")
        self.assertEqual(translation.pending_content, "Community translation in English")
        self.assertEqual(translation.source, CommentTranslation.Source.HUMAN)
        self.assertFalse(translation.is_preferred)
        self.assertFalse(translation.is_approved)
        self.assertIsNone(translation.translated_by)
        self.assertEqual(translation.pending_translated_by, self.user)

    def test_staff_user_can_approve_translation_immediately(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        self.client.force_login(self.staff_user)

        with override("en"):
            response = self.client.post(
                reverse("comments:suggest_comment_translation", kwargs={"comment_id": comment.id}),
                {
                    "language": "en",
                    "content": "Community translation in English",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["pending_review"])

        translation = CommentTranslation.objects.get(comment=comment, language="en")
        self.assertEqual(translation.source, CommentTranslation.Source.HUMAN)
        self.assertEqual(translation.content, "Community translation in English")
        self.assertTrue(translation.is_preferred)
        self.assertTrue(translation.is_approved)
        self.assertEqual(translation.translated_by, self.staff_user)
        self.assertFalse(translation.pending_content)

    def test_pending_human_suggestion_does_not_replace_visible_machine_translation(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        CommentTranslation.objects.create(
            comment=comment,
            language="en",
            content="Automatic translation in English",
            source=CommentTranslation.Source.MACHINE,
            provider="deepl",
            is_preferred=True,
            is_approved=True,
        )
        self.client.force_login(self.user)

        with override("en"):
            response = self.client.post(
                reverse("comments:suggest_comment_translation", kwargs={"comment_id": comment.id}),
                {
                    "language": "en",
                    "content": "Community translation in English",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["pending_review"])

        translation = CommentTranslation.objects.get(comment=comment, language="en")
        self.assertEqual(translation.source, CommentTranslation.Source.MACHINE)
        self.assertEqual(translation.content, "Automatic translation in English")
        self.assertEqual(translation.pending_content, "Community translation in English")
        self.assertTrue(translation.is_preferred)
        self.assertTrue(translation.is_approved)

        with override("en"):
            response = self.client.get(self.post.get_absolute_url_for_language("en"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automatic translation")
        self.assertContains(response, "Automatic translation in English")
        self.assertNotContains(response, "Community translation in English")

    def test_approved_human_translation_is_preferred_over_machine_translation(self):
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            author_name="Commenter",
            author_email=self.user.email,
            content="Comentario original en español",
            language="es",
            is_approved=True,
        )
        CommentTranslation.objects.create(
            comment=comment,
            language="en",
            content="Automatic translation in English",
            source=CommentTranslation.Source.MACHINE,
            provider="deepl",
            is_preferred=True,
            is_approved=True,
        )
        self.client.force_login(self.staff_user)

        with override("en"):
            response = self.client.post(
                reverse("comments:suggest_comment_translation", kwargs={"comment_id": comment.id}),
                {
                    "language": "en",
                    "content": "Community translation in English",
                },
            )

        self.assertEqual(response.status_code, 200)

        with override("en"):
            response = self.client.get(self.post.get_absolute_url_for_language("en"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Community translation in English")
        self.assertNotContains(response, "Automatic translation in English")
