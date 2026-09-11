from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


_LANGUAGE_LABELS = {
    "es": {"es": "español", "en": "Spanish", "ca": "espanyol"},
    "en": {"es": "inglés", "en": "English", "ca": "anglès"},
    "ca": {"es": "catalán", "en": "Catalan", "ca": "català"},
}

class Source(TranslatableModel):
    """A primary document or publication that can be cited by any content."""

    # These columns were part of the original single-language source table.
    # They remain in production databases while the public/editorial values
    # live in parler translations. Keeping internal aliases lets new Source
    # rows satisfy the legacy NOT NULL columns without exposing two sets of
    # fields in the CMS.
    legacy_title = models.CharField(
        max_length=500,
        db_column="title",
        editable=False,
        default="",
    )
    legacy_bibliographic_reference = models.TextField(
        db_column="bibliographic_reference",
        editable=False,
        default="",
    )
    legacy_summary = models.TextField(
        db_column="summary",
        editable=False,
        default="",
    )

    class SourceType(models.TextChoices):
        LAW = "law", _("Law or regulation")
        DIRECTIVE = "directive", _("Directive or international regulation")
        OFFICIAL_GUIDANCE = "official_guidance", _("Official guidance")
        STANDARD = "standard", _("Technical standard")
        SCIENTIFIC_ARTICLE = "scientific_article", _("Scientific article")
        REPORT = "report", _("Report")
        BOOK = "book", _("Book")
        WEB = "web", _("Web resource")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        VERIFIED = "verified", _("Verified")
        ARCHIVED = "archived", _("Archived")

    translations = TranslatedFields(
        title=models.CharField(max_length=500, verbose_name=_("Title")),
        bibliographic_reference=models.TextField(
            blank=True,
            verbose_name=_("Bibliographic reference"),
            help_text=_(
                "Full reference: original title, authors, editor, place, year, "
                "ISBN/ISSN/DOI and other permanent identification data."
            ),
        ),
        summary=models.TextField(
            blank=True,
            verbose_name=_("Source description"),
            help_text=_(
                "Explain the value of this source. It is shown to readers in a "
                "collapsible panel."
            ),
        ),
        localized_url=models.URLField(blank=True, verbose_name=_("Official URL for this language")),
    )

    organisation = models.CharField(max_length=250, blank=True, verbose_name=_("Organisation or author"))
    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.WEB,
        verbose_name=_("Source type"),
    )
    publication_date = models.DateField(null=True, blank=True, verbose_name=_("Publication date"))
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="es",
        verbose_name=_("Original language"),
    )
    url = models.URLField(blank=True, verbose_name=_("Official URL"))
    document_url = models.URLField(
        blank=True,
        verbose_name=_("Direct document URL"),
        help_text=_(
            "Optional direct link to the PDF or other original document. Keep "
            "the official landing page in Official URL."
        ),
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Verification status"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Source")
        verbose_name_plural = _("Sources")
        ordering = ("organisation", "pk")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled source"))

    def save(self, *args, **kwargs):
        """Mirror the initial translation into legacy database columns.

        The aliases are a compatibility layer only. Editors still manage the
        translated fields declared above, while older database schemas keep
        receiving the non-null values they require on insertion.
        """
        if self._state.adding:
            self.legacy_title = self.safe_translation_getter("title", any_language=True) or ""
            self.legacy_bibliographic_reference = (
                self.safe_translation_getter("bibliographic_reference", any_language=True) or ""
            )
            self.legacy_summary = self.safe_translation_getter("summary", any_language=True) or ""
        super().save(*args, **kwargs)

    @property
    def display_title(self):
        return (
            self.safe_translation_getter(
                "title",
                language_code=get_language(),
                any_language=True,
            )
            or str(_("Untitled source"))
        )

    @property
    def display_bibliographic_reference(self):
        return (
            self.safe_translation_getter(
                "bibliographic_reference",
                language_code=get_language(),
                any_language=True,
            )
            or self.display_title
        )

    @property
    def display_url(self):
        return (
            self.safe_translation_getter(
                "localized_url",
                language_code=get_language(),
                any_language=False,
            )
            or self.url
        )

    @property
    def display_summary(self):
        return self.safe_translation_getter(
            "summary",
            language_code=get_language(),
            any_language=True,
        )

    @property
    def uses_original_document_url(self):
        """Whether the active language falls back to the original document."""
        active_language = (get_language() or "es").split("-")[0]
        localized_url = self.safe_translation_getter(
            "localized_url",
            language_code=active_language,
            any_language=False,
        )
        return bool(
            self.url
            and active_language != self.language
            and not localized_url
        )

    @property
    def original_document_availability_note(self):
        """Small localized notice shown only when no local official URL exists."""
        if not self.uses_original_document_url:
            return ""

        active_language = (get_language() or "es").split("-")[0]
        original_language_label = _LANGUAGE_LABELS.get(
            self.language,
            _LANGUAGE_LABELS["es"],
        ).get(active_language, self.language)
        templates = {
            "es": "Documentación original disponible en {}.",
            "en": "Original documentation available in {}.",
            "ca": "Documentació original disponible en {}.",
        }
        return templates.get(active_language, templates["es"]).format(
            original_language_label
        )


class Citation(models.Model):
    """Links a source to a Post, Page, Publication, or future content model."""

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="citations",
        verbose_name=_("Source"),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content type"),
    )
    object_id = models.PositiveBigIntegerField(verbose_name=_("Content ID"))
    content_object = GenericForeignKey("content_type", "object_id")
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="es",
        verbose_name=_("Content language"),
    )
    order = models.PositiveSmallIntegerField(default=1, verbose_name=_("Display order"))
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_("Primary source"),
        help_text=_("Mark the source that provides the main evidence for this content."),
    )
    locator = models.CharField(
        max_length=250,
        blank=True,
        verbose_name=_("Page, section or locator"),
        help_text=_("For example: Article 14, page 24, or section 3."),
    )
    note = models.TextField(
        blank=True,
        verbose_name=_("Editorial note"),
        help_text=_(
            "Optional explanation of how this source supports this content, "
            "including relevant sections or pages. It is shown in a collapsible panel."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Citation")
        verbose_name_plural = _("Citations")
        ordering = ("content_type", "object_id", "language", "order", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "content_type", "object_id", "language"),
                name="unique_source_citation_per_content_language",
            )
        ]

    def __str__(self):
        return f"{self.source} → {self.content_object}"
