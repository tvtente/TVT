from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from categories.models import Category

from .rendering import render_markdown_to_html


User = get_user_model()


class Notebook(TranslatableModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    translations = TranslatedFields(
        title=models.CharField(max_length=250, verbose_name=_("Title")),
        slug=models.SlugField(max_length=250, verbose_name=_("Slug")),
        abstract=models.TextField(blank=True, verbose_name=_("Abstract")),
        markdown_source=models.TextField(
            blank=True,
            verbose_name=_("Markdown source"),
            help_text=_("Paste Markdown exported from Jupyter or written manually."),
        ),
        rendered_html=models.TextField(
            blank=True,
            editable=False,
            verbose_name=_("Rendered HTML"),
            help_text=_("Generated automatically from the Markdown source on save."),
        ),
        trusted_html_fragment=models.TextField(
            blank=True,
            verbose_name=_("Trusted interactive HTML"),
            help_text=_(
                "Optional self-contained HTML fragment for trusted embeds such as Plotly exports with inline JS."
            ),
        ),
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
        keywords=models.CharField(
            max_length=300,
            blank=True,
            verbose_name=_("Keywords"),
        ),
        meta={
            "unique_together": [("language_code", "slug")],
        },
    )

    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="notebooks",
        verbose_name=_("Author"),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="notebooks",
        verbose_name=_("Categories"),
    )
    source_notebook = models.FileField(
        upload_to="notebooks/source/",
        blank=True,
        null=True,
        verbose_name=_("Source notebook (.ipynb)"),
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Published at"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )

    class Meta:
        verbose_name = _("Notebook")
        verbose_name_plural = _("Notebooks")
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    def save(self, *args, **kwargs):
        language_code = self.get_current_language() or get_language() or "es"
        markdown_source = self.safe_translation_getter(
            "markdown_source",
            language_code=language_code,
            any_language=False,
        ) or ""
        self.set_current_language(language_code)
        self.rendered_html = render_markdown_to_html(markdown_source)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        translated_slug = (
            self.safe_translation_getter("slug", language_code=get_language(), any_language=False)
            or self.safe_translation_getter("slug", any_language=True)
            or self.translations.values_list("slug", flat=True).first()
        )
        return reverse("notebooks:notebook_detail", kwargs={"slug": translated_slug})

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    @property
    def translated_abstract(self):
        return self.safe_translation_getter("abstract", any_language=True) or ""

    @property
    def translated_rendered_html(self):
        return self.safe_translation_getter("rendered_html", any_language=True) or ""

    @property
    def translated_trusted_html_fragment(self):
        return self.safe_translation_getter("trusted_html_fragment", any_language=True) or ""
