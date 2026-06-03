# File: publications/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from django.urls import reverse
from django.utils import timezone
from categories.models import Category
from tinymce.models import HTMLField
from django.utils.translation import get_language


User = get_user_model()


class Publication(TranslatableModel):
    """
    📄 Represents a scientific or academic publication, designed for long-term preservation and export.

    Publications are structured as research-style documents instead of generic long-form content.
    """

    # 🔤 Translatable Fields
    translations = TranslatedFields(
        title=models.CharField(
            max_length=250,
            verbose_name=_("Title"),
            help_text=_("Recommended length: 5–15 words."),
        ),
        slug=models.SlugField(
            max_length=250,
            unique=False,
            verbose_name=_("Slug"),
        ),
        abstract=HTMLField(
            blank=True,
            verbose_name=_("Abstract"),
            help_text=_("Summarize objectives, methods, and key findings. Recommended length: 150–250 words."),
        ),

        # ====================================================
        # Structured scientific sections
        # These fields replace the old generic Full Content field.
        # ====================================================

        introduction=HTMLField(
            blank=True,
            verbose_name=_("Introduction"),
            help_text=_(
                "Contextualize the problem, justify the study, and introduce the research topic. "
                "Recommended length: 300–800 words."
            ),
        ),
        theoretical_framework=HTMLField(
            blank=True,
            verbose_name=_("Theoretical framework"),
            help_text=_(
                "Develop the conceptual foundation, key authors, theories, and relevant prior work. "
                "Recommended length: 500–1000 words."
            ),
        ),
        objectives_hypotheses=HTMLField(
            blank=True,
            verbose_name=_("Objectives and hypotheses"),
            help_text=_(
                "Define research questions, objectives, and hypotheses. "
                "Recommended length: 100–200 words."
            ),
        ),
        methodology=HTMLField(
            blank=True,
            verbose_name=_("Methodology"),
            help_text=_(
                "Describe the research design, sample, instruments, data collection, and analysis techniques. "
                "Recommended length: 300–600 words."
            ),
        ),
        results=HTMLField(
            blank=True,
            verbose_name=_("Results"),
            help_text=_(
                "Present findings, data, tables, figures, categories, or statistical results. "
                "Recommended length: 300–700 words."
            ),
        ),
        discussion=HTMLField(
            blank=True,
            verbose_name=_("Discussion"),
            help_text=_(
                "Interpret findings, compare them with the literature, and discuss implications and limitations. "
                "Recommended length: 400–800 words."
            ),
        ),
        conclusions=HTMLField(
            blank=True,
            verbose_name=_("Conclusions"),
            help_text=_(
                "Answer the research questions and highlight the main contributions. "
                "Recommended length: 100–200 words."
            ),
        ),
        references=HTMLField(
            blank=True,
            verbose_name=_("References / Bibliography"),
            help_text=_(
                "List all cited sources, books, academic articles, reports, DOI links, or URLs. "
                "Recommended: 5–20 sources when applicable."
            ),
        ),
        annexes=HTMLField(
            blank=True,
            verbose_name=_("Annexes"),
            help_text=_(
                "Optional supplementary material such as questionnaires, raw data, transcripts, or software used."
            ),
        ),

        # ====================================================
        # SEO / media
        # ====================================================

        meta_title=models.CharField(
            max_length=70,
            blank=True,
            null=True,
            verbose_name=_("Meta Title"),
        ),
        meta_description=models.CharField(
            max_length=160,
            blank=True,
            null=True,
            verbose_name=_("Meta Description"),
        ),
        featured_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Featured image (library)"),
            help_text=_("Primary publication cover image from Media Library."),
        ),
        social_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Social image (library)"),
            help_text=_("Square or social-preview image from Media Library, used near the abstract and in cards/previews."),
        ),
        mobile_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Mobile image (library)"),
            help_text=_("Vertical 9:16 image from Media Library for mobile-first widgets or layouts."),
        ),
    )

    # 🔗 Core Relations
    authors = models.ManyToManyField(
        User,
        related_name="publications",
        verbose_name=_("Authors"),
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="publications",
        verbose_name=_("Categories"),
    )

    # 📚 Academic Metadata
    doi = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("DOI"),
    )

    # 🖼️ Media & Files
    attachment = models.FileField(
        upload_to="publications/files/",
        blank=True,
        null=True,
        verbose_name=_("Full PDF"),
    )

    # 🕒 Timeline
    publication_date = models.DateField(
        default=timezone.now,
        verbose_name=_("Publication Date"),
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_("Is Published?"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        verbose_name = _("Publication")
        verbose_name_plural = _("Publications")
        ordering = ["-publication_date"]

    def __str__(self):
        title = self.safe_translation_getter("title", any_language=True)
        return str(title) if title else str(_("Untitled"))

    def get_absolute_url(self):
        return reverse(
            "publications:publication_detail",
            kwargs={
                "slug": self.safe_translation_getter("slug", any_language=True),
            },
        )

    def get_authors_display(self):
        return ", ".join(
            [
                author.get_full_name() or author.username
                for author in self.authors.all()
            ]
        )

    # 📂 Categories display logic
    def get_categories_display(self):
        lang = get_language()
        return ", ".join(
            [
                getattr(category, f"name_{lang}", category.name)
                for category in self.categories.all()
            ]
        )

    @staticmethod
    def _file_from_gallery_asset(asset):
        if asset is None:
            return None

        file_obj = getattr(asset, "image", None)

        if file_obj and getattr(file_obj, "name", ""):
            return file_obj

        return None

    def get_featured_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "featured_image_asset",
            language_code=language_code,
            any_language=False,
        )
        return self._file_from_gallery_asset(asset)

    def get_social_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "social_image_asset",
            language_code=language_code,
            any_language=False,
        )
        return self._file_from_gallery_asset(asset)

    def get_mobile_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "mobile_image_asset",
            language_code=language_code,
            any_language=False,
        )
        from_asset = self._file_from_gallery_asset(asset)
        if from_asset:
            return from_asset
        return self.get_featured_image(language_code=language_code)
