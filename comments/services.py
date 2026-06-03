import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from comments.models import CommentTranslation


class CommentTranslationError(Exception):
    pass


class CommentTranslationDisabled(CommentTranslationError):
    pass


class UnsupportedCommentTranslationProvider(CommentTranslationError):
    pass


class CommentTranslationMisconfigured(CommentTranslationError):
    pass


class BaseCommentTranslationProvider:
    provider_name = ""
    source = CommentTranslation.Source.MACHINE

    def translate(self, text, source_language, target_language):
        raise NotImplementedError


class MockCommentTranslationProvider(BaseCommentTranslationProvider):
    provider_name = "mock"

    def translate(self, text, source_language, target_language):
        return f"[{target_language}] {text}"


class DeepLCommentTranslationProvider(BaseCommentTranslationProvider):
    provider_name = "deepl"

    def __init__(self):
        self.api_key = getattr(settings, "DEEPL_API_KEY", "").strip()
        self.api_url = getattr(
            settings,
            "DEEPL_API_URL",
            "https://api-free.deepl.com/v2/translate",
        ).strip()
        self.timeout = getattr(settings, "COMMENT_TRANSLATION_TIMEOUT", 10)

        if not self.api_key:
            raise CommentTranslationMisconfigured(
                _("DeepL translation is enabled but DEEPL_API_KEY is missing.")
            )

    @staticmethod
    def _normalize_language_code(language_code):
        return str(language_code or "").split("-")[0].strip().upper()

    def translate(self, text, source_language, target_language):
        payload = {
            "text": [text],
            "target_lang": self._normalize_language_code(target_language),
        }
        normalized_source = self._normalize_language_code(source_language)
        if normalized_source:
            payload["source_lang"] = normalized_source

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"DeepL-Auth-Key {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommentTranslationError(
                _("The translation provider could not be reached right now.")
            ) from exc

        data = response.json()
        translated_items = data.get("translations") or []
        if not translated_items or not translated_items[0].get("text"):
            raise CommentTranslationError(
                _("The requested translation could not be generated.")
            )
        return translated_items[0]["text"]


def get_comment_translation_provider():
    provider_name = getattr(settings, "COMMENT_TRANSLATION_PROVIDER", "disabled").strip().lower()

    if provider_name in {"", "disabled", "none"}:
        raise CommentTranslationDisabled(
            _("Automatic translation is not available right now.")
        )
    if provider_name == "mock":
        return MockCommentTranslationProvider()
    if provider_name == "deepl":
        return DeepLCommentTranslationProvider()
    raise UnsupportedCommentTranslationProvider(
        _("Unsupported comment translation provider.")
    )


def get_or_create_comment_translation(comment, target_language, *, requested_by=None):
    if target_language == comment.language:
        return None, False

    translation = comment.translations.filter(language=target_language).first()
    if translation:
        return translation, False

    if (
        comment.translation_language == target_language
        and comment.translated_content
    ):
        translation, created = CommentTranslation.objects.get_or_create(
            comment=comment,
            language=target_language,
            defaults={
                "content": comment.translated_content,
                "source": CommentTranslation.Source.HUMAN,
                "provider": "",
                "translated_by": comment.translated_by,
            },
        )
        return translation, created

    provider = get_comment_translation_provider()
    translated_text = provider.translate(
        comment.content,
        comment.language,
        target_language,
    )
    translation = CommentTranslation.objects.create(
        comment=comment,
        language=target_language,
        content=translated_text,
        source=provider.source,
        provider=provider.provider_name,
        translated_by=requested_by if getattr(requested_by, "is_authenticated", False) else None,
    )
    return translation, True
