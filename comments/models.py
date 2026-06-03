import logging

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.translation import get_language, gettext_lazy as _
from posts.models import Post  # 👈 Ajusta si cambia el nombre del modelo o app
from django.utils import timezone
from accounts.models import get_user_avatar_url

User = get_user_model()
logger = logging.getLogger(__name__)


class CommentTranslation(models.Model):
    class Source(models.TextChoices):
        HUMAN = "human", _("Human")
        MACHINE = "machine", _("Machine")

    comment = models.ForeignKey(
        "Comment",
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Comment"),
    )
    language = models.CharField(
        max_length=10,
        verbose_name=_("Language"),
    )
    content = models.TextField(
        verbose_name=_("Translated Content"),
    )
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.HUMAN,
        verbose_name=_("Translation source"),
    )
    provider = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Translation provider"),
        help_text=_("Optional provider or engine name for machine translations."),
    )
    translated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comment_translations",
        verbose_name=_("Translated by"),
        help_text=_("User who provided the translation, if different from the author."),
    )
    pending_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Pending suggested content"),
    )
    pending_translated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_comment_translation_suggestions",
        verbose_name=_("Pending suggested by"),
        help_text=_("User who suggested a human translation pending moderation."),
    )
    pending_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Pending suggested at"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name=_("Is preferred?"),
        help_text=_("Whether this translation should be shown before other alternatives for the same language."),
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name=_("Is approved?"),
        help_text=_("Whether this translation is approved for public display."),
    )

    class Meta:
        verbose_name = _("Comment translation")
        verbose_name_plural = _("Comment translations")
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "language"],
                name="unique_comment_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.comment_id}:{self.language}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_preferred:
            self.__class__.objects.filter(
                comment=self.comment,
                language=self.language,
            ).exclude(pk=self.pk).update(is_preferred=False)

    def submit_human_suggestion(self, content, user, *, auto_approve=False):
        if auto_approve:
            self.content = content
            self.source = self.Source.HUMAN
            self.provider = ""
            self.translated_by = user
            self.is_approved = True
            self.is_preferred = True
            self.pending_content = ""
            self.pending_translated_by = None
            self.pending_created_at = None
            self.save()
            return "approved"

        self.pending_content = content
        self.pending_translated_by = user
        self.pending_created_at = timezone.now()
        self.save(
            update_fields=[
                "pending_content",
                "pending_translated_by",
                "pending_created_at",
                "updated_at",
            ]
        )
        return "pending"

    def approve_pending_suggestion(self):
        if not self.pending_content:
            return False

        self.content = self.pending_content
        self.source = self.Source.HUMAN
        self.provider = ""
        self.translated_by = self.pending_translated_by or self.translated_by
        self.is_approved = True
        self.is_preferred = True
        self.pending_content = ""
        self.pending_translated_by = None
        self.pending_created_at = None
        self.save()
        return True

    def reject_pending_suggestion(self):
        if not self.pending_content:
            return False
        self.pending_content = ""
        self.pending_translated_by = None
        self.pending_created_at = None
        self.save(
            update_fields=[
                "pending_content",
                "pending_translated_by",
                "pending_created_at",
                "updated_at",
            ]
        )
        return True


class Comment(MPTTModel):
    """
    🗨️ Represents a nested, user-submitted comment.
    Includes moderation, translation metadata and nesting (via MPTT).
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_("Post")
    )

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        verbose_name=_("Parent Comment")
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comments_made_by',
        verbose_name=_("User")
    )

    author_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Author Name")
    )

    author_email = models.EmailField(
        blank=True,
        verbose_name=_("Author Email")
    )

    content = models.TextField(verbose_name=_("Content"))
    language = models.CharField(max_length=10, default='en', verbose_name=_("Original Language"))

    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created At"))
    is_approved = models.BooleanField(default=False, verbose_name=_("Is Approved?"))

    # 🈯️ Translation metadata
    translated_content = models.TextField(blank=True, null=True, verbose_name=_("Translated Content"))
    translated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="translated_comments",
        verbose_name=_("Translated by"),
        help_text=_("User who provided the translation, if different from the author.")
    )
    translation_language = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_("Translation Language")
    )

    class MPTTMeta:
        order_insertion_by = ['created_at']

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")

    def __str__(self):
        lang_note = f"[{self.language}]" if self.language else ""
        return f"{'—' * self.level} {self.get_display_author()} {lang_note}"

    def get_display_author(self):
        if not self.user:
            return self.author_name
        try:
            return self.user.profile.get_display_name()
        except ObjectDoesNotExist:
            return self.user.username
        except AttributeError:
            logger.warning(
                _("Failed to resolve the comment author display name from the profile."),
                exc_info=True,
            )
            return self.user.username

    def get_display_content(self, preferred_language=None):
        """
        💬 Returns translated content if applicable and requested.
        """
        preferred_language = preferred_language or get_language()
        if preferred_language:
            translation = self.translations.filter(
                language=preferred_language,
                is_approved=True,
            ).order_by(
                "-is_preferred",
                "source",
                "-created_at",
            ).first()
            if translation and translation.content:
                return translation.content
            if (
                preferred_language == self.translation_language
                and self.translated_content
            ):
                return self.translated_content
        return self.content

    def has_translation_for(self, language_code=None):
        language_code = language_code or get_language()
        if not language_code:
            return False
        if self.translations.filter(
            language=language_code,
            is_approved=True,
        ).exists():
            return True
        return (
            language_code == self.translation_language
            and bool(self.translated_content)
        )

    def get_original_content(self):
        return self.content

    def get_language_label(self):
        languages = dict(settings.LANGUAGES)
        return languages.get(self.language, (self.language or "").upper())

    def get_translation_for(self, language_code=None):
        language_code = language_code or get_language()
        if not language_code:
            return None
        translation = self.translations.filter(
            language=language_code,
            is_approved=True,
        ).order_by(
            "-is_preferred",
            "source",
            "-created_at",
        ).first()
        if translation:
            return translation
        if (
            language_code == self.translation_language
            and self.translated_content
        ):
            return {
                "content": self.translated_content,
                "source": CommentTranslation.Source.HUMAN,
                "provider": "",
                "translated_by": self.translated_by,
                "is_preferred": True,
                "is_approved": True,
            }
        return None

    def get_translation_source_label(self, language_code=None):
        translation = self.get_translation_for(language_code)
        if not translation:
            return ""

        source = translation.source if hasattr(translation, "source") else translation.get("source")
        if source == CommentTranslation.Source.MACHINE:
            return _("Automatic translation")
        return _("Community translation")

    def get_translation_credit_label(self, language_code=None):
        translation = self.get_translation_for(language_code)
        if not translation:
            return ""

        source = translation.source if hasattr(translation, "source") else translation.get("source")
        translated_by = (
            translation.translated_by if hasattr(translation, "translated_by")
            else translation.get("translated_by")
        )

        if source != CommentTranslation.Source.HUMAN:
            return ""

        if translated_by:
            try:
                display_name = translated_by.profile.get_display_name()
            except ObjectDoesNotExist:
                display_name = translated_by.username
            except AttributeError:
                logger.warning(
                    _("Failed to resolve the comment translation credit display name from the profile."),
                    exc_info=True,
                )
                display_name = translated_by.username
            return _("Translated by %(user)s") % {"user": display_name}

        return _("Translated by community")

    def get_author_name(self):
        if self.user:
            try:
                return self.user.profile.get_display_name()
            except ObjectDoesNotExist:
                return self.user.username
            except AttributeError:
                logger.warning(
                    _("Failed to resolve the comment author display name from the profile."),
                    exc_info=True,
                )
                return self.user.username
        return self.author_name
    
    def get_author_avatar_url(self):
        return get_user_avatar_url(self.user)
