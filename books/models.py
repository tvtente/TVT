from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from tinymce.models import HTMLField

from categories.models import Category


User = get_user_model()


class Book(TranslatableModel):
    translations = TranslatedFields(
        title=models.CharField(
            max_length=250,
            verbose_name=_("Title"),
        ),
        slug=models.SlugField(
            max_length=250,
            unique=False,
            verbose_name=_("Slug"),
        ),
        subtitle=models.CharField(
            max_length=300,
            blank=True,
            verbose_name=_("Subtitle"),
        ),
        description=HTMLField(
            blank=True,
            verbose_name=_("Description"),
        ),
        excerpt=HTMLField(
            blank=True,
            verbose_name=_("Excerpt"),
        ),
        table_of_contents=HTMLField(
            blank=True,
            verbose_name=_("Table of contents"),
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
        cover_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Cover image (library)"),
            help_text=_("Primary book cover from Media Library."),
        ),
        social_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Social image (library)"),
            help_text=_("Square or social-preview image from Media Library."),
        ),
        mobile_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Mobile image (library)"),
            help_text=_("Vertical 9:16 image optimized for mobile layouts."),
        ),
        preview_pdf=models.FileField(
            upload_to="books/previews/",
            blank=True,
            null=True,
            verbose_name=_("Preview PDF"),
        ),
        full_pdf=models.FileField(
            upload_to="books/files/",
            blank=True,
            null=True,
            verbose_name=_("Full PDF"),
        ),
    )

    authors = models.ManyToManyField(
        User,
        related_name="books",
        verbose_name=_("Authors"),
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="books",
        verbose_name=_("Categories"),
    )
    isbn = models.CharField(
        max_length=32,
        blank=True,
        verbose_name=_("ISBN"),
    )
    publication_date = models.DateField(
        default=timezone.now,
        verbose_name=_("Publication Date"),
    )
    is_published = models.BooleanField(
        default=False,
        verbose_name=_("Is Published?"),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_("Price"),
    )
    currency = models.CharField(
        max_length=3,
        default="EUR",
        verbose_name=_("Currency"),
    )
    allow_free_preview = models.BooleanField(
        default=True,
        verbose_name=_("Allow Free Preview"),
    )
    requires_purchase = models.BooleanField(
        default=False,
        verbose_name=_("Requires Purchase"),
    )
    available_from = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Available from"),
        help_text=_("Optional release date for the purchasable full edition."),
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
        verbose_name = _("Book")
        verbose_name_plural = _("Books")
        ordering = ["-publication_date", "-created_at"]

    def __str__(self):
        title = self.safe_translation_getter("title", any_language=True)
        return str(title) if title else str(_("Untitled"))

    def get_absolute_url(self):
        return reverse(
            "books:book_detail",
            kwargs={
                "slug": self.safe_translation_getter("slug", any_language=True),
            },
        )

    def get_preview_url(self):
        return reverse(
            "books:book_reader",
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

    def get_categories_display(self):
        lang = get_language()
        return ", ".join(
            [
                category.safe_translation_getter(
                    "name",
                    language_code=lang,
                    any_language=True,
                )
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

    def get_cover_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "cover_image_asset",
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
        from_asset = self._file_from_gallery_asset(asset)
        if from_asset:
            return from_asset
        return self.get_cover_image(language_code=language_code)

    def get_mobile_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "mobile_image_asset",
            language_code=language_code,
            any_language=False,
        )
        from_asset = self._file_from_gallery_asset(asset)
        if from_asset:
            return from_asset
        return self.get_cover_image(language_code=language_code)

    def get_preview_pdf(self, language_code=None, any_language=False):
        return self.safe_translation_getter(
            "preview_pdf",
            language_code=language_code,
            any_language=any_language,
        )

    def get_full_pdf(self, language_code=None, any_language=False):
        return self.safe_translation_getter(
            "full_pdf",
            language_code=language_code,
            any_language=any_language,
        )

    def has_preview_pdf_in_any_language(self):
        return bool(self.get_preview_pdf(any_language=True))

    def has_full_pdf_in_any_language(self):
        return bool(self.get_full_pdf(any_language=True))

    def is_available_for_purchase(self):
        if not (self.is_published and self.requires_purchase and self.price is not None):
            return False
        if not self.has_full_pdf_in_any_language():
            return False
        if self.available_from and self.available_from > timezone.localdate():
            return False
        return True

    def is_coming_soon(self):
        return bool(
            self.requires_purchase
            and (
                not self.has_full_pdf_in_any_language()
                or (self.available_from and self.available_from > timezone.localdate())
            )
        )
