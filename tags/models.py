# File: tags/models.py

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

class Tag(TranslatableModel):
    """
    🐝 Multilingual Tag model for categorizing content.
    """
    translations = TranslatedFields(
        label=models.CharField(max_length=250, verbose_name=_("Label")),
        translated_slug=models.SlugField(
            max_length=250,
            blank=True,
            verbose_name=_("Slug for this Language"),
            help_text=_("Optional language-specific slug. Falls back to the global slug.")
        )
    )
    slug = models.SlugField(unique=True, max_length=250, verbose_name=_("Slug"))
    click_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Tag Click Score"),
        help_text=_("Increases by 1 when visitors open this tag from a tag link.")
    )

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.safe_translation_getter("label", any_language=True)

    def get_slug(self):
        return self.safe_translation_getter('translated_slug', any_language=False) or self.slug

    def get_absolute_url(self):
        return reverse('posts:posts_by_tag', kwargs={'tag_slug': self.get_slug()})


class TaggedPost(models.Model):
    """
    🧩 Through model linking Tags to Posts, with optional metadata.
    """
    post = models.ForeignKey(
        'posts.Post',  # ✅ Usamos una referencia perezosa por string
        on_delete=models.CASCADE,
        related_name="tag_links",
        verbose_name=_("Post"),
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="post_links",
        verbose_name=_("Tag"),
    )
    language = models.CharField(
        max_length=10,
        default='es',
        choices=settings.LANGUAGES,
        verbose_name=_("Language"),
        help_text=_("Language of the post translation where this tag applies.")
    )

    relevance_score = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Relevance Score"),
        help_text=_("Optional score from 0 to 100 indicating tag relevance."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Assigned At"))

    class Meta:
        unique_together = ("post", "tag", "language")
        verbose_name = _("Tagged Post")
        verbose_name_plural = _("Tagged Posts")

    def __str__(self):
        return f"{self.tag} → {self.post}"


class TagDailyMetric(models.Model):
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='daily_metrics',
        verbose_name=_("Tag"),
    )
    date = models.DateField(verbose_name=_("Date"))
    click_count = models.PositiveIntegerField(default=0, verbose_name=_("Daily Click Score"))

    class Meta:
        verbose_name = _("Tag Daily Metric")
        verbose_name_plural = _("Tag Daily Metrics")
        unique_together = ('tag', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['tag', 'date']),
        ]

    def __str__(self):
        return f"{self.tag} - {self.date}: {self.click_count}"
